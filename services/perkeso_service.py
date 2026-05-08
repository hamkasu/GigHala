"""
PERKESO GIG Workers API Integration Service
Handles all communication with PERKESO's PRIHATIN system per GIG Workers API v2.1.

Flow:
1. Platform registers each gig worker with PERKESO before submitting deductions.
2. On every completed job, platform submits a deduction (1.25% of job amount).
3. PERKESO sends async callbacks for batch operations and deduction results.

Environments:
  Sandbox:    https://gig-sandbox.perkeso.gov.my
  Production: https://gig-connector.perkeso.gov.my
"""

import os
import time
import logging
import requests
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

PERKESO_ENVIRONMENTS = {
    'sandbox': 'https://gig-sandbox.perkeso.gov.my',
    'production': 'https://gig-connector.perkeso.gov.my',
}

DEFAULT_SECTOR_CODE = 'P'  # SERVICE PROVIDER — most common for gig workers


class PERKESOError(Exception):
    """Raised when PERKESO API returns a non-success status or HTTP error."""
    def __init__(self, message, status_code=None, response_data=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class PERKESOService:
    """
    Client for the PERKESO GIG Workers API v2.1.

    Manages OAuth2 client-credentials tokens automatically (cached in memory;
    tokens are valid for 1 year but we refresh after 23 hours to be safe).
    """

    _token: str | None = None
    _token_expires_at: float = 0.0  # unix timestamp

    def __init__(self):
        self.environment = os.environ.get('PERKESO_ENVIRONMENT', 'sandbox')
        self.base_url = PERKESO_ENVIRONMENTS.get(self.environment,
                                                  PERKESO_ENVIRONMENTS['sandbox'])
        self.client_id = os.environ.get('PERKESO_CLIENT_ID', '')
        self.client_secret = os.environ.get('PERKESO_CLIENT_SECRET', '')
        self.timeout = 30  # seconds

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    def _is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def _token_valid(self) -> bool:
        return bool(PERKESOService._token) and time.time() < PERKESOService._token_expires_at

    def generate_token(self) -> str:
        """
        POST /oauth/token — exchange client credentials for a bearer token.
        Caches the token in-process; refreshes when within 1 hour of expiry.
        """
        payload = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }
        resp = requests.post(
            f'{self.base_url}/oauth/token',
            json=payload,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        PERKESOService._token = data['access_token']
        expires_in = data.get('expires_in', 31536000)
        # Refresh 1 hour before actual expiry
        PERKESOService._token_expires_at = time.time() + expires_in - 3600
        logger.info('PERKESO token generated successfully (env=%s)', self.environment)
        return PERKESOService._token

    def _get_token(self) -> str:
        if not self._token_valid():
            self.generate_token()
        return PERKESOService._token

    def _headers(self) -> dict:
        return {
            'Authorization': f'Bearer {self._get_token()}',
            'Content-Type': 'application/json',
        }

    # ------------------------------------------------------------------
    # Internal HTTP helpers
    # ------------------------------------------------------------------

    def _get(self, path: str, params: dict = None) -> dict:
        resp = requests.get(
            f'{self.base_url}{path}',
            headers=self._headers(),
            params=params,
            timeout=self.timeout,
        )
        return self._handle(resp)

    def _post(self, path: str, payload: dict) -> dict:
        resp = requests.post(
            f'{self.base_url}{path}',
            headers=self._headers(),
            json=payload,
            timeout=self.timeout,
        )
        return self._handle(resp)

    def _patch(self, path: str, payload: dict) -> dict:
        resp = requests.patch(
            f'{self.base_url}{path}',
            headers=self._headers(),
            json=payload,
            timeout=self.timeout,
        )
        return self._handle(resp)

    def _put(self, path: str, payload: dict = None) -> dict:
        resp = requests.put(
            f'{self.base_url}{path}',
            headers=self._headers(),
            json=payload or {},
            timeout=self.timeout,
        )
        return self._handle(resp)

    @staticmethod
    def _handle(resp: requests.Response) -> dict:
        """Parse JSend response; raise PERKESOError on non-success."""
        try:
            data = resp.json()
        except Exception:
            resp.raise_for_status()
            raise PERKESOError(f'Non-JSON response: {resp.text}', resp.status_code)

        if resp.status_code not in (200, 202):
            raise PERKESOError(
                data.get('message', f'HTTP {resp.status_code}'),
                status_code=resp.status_code,
                response_data=data,
            )

        status = data.get('status')
        if status == 'error':
            raise PERKESOError(
                data.get('message', 'Unknown PERKESO error'),
                status_code=resp.status_code,
                response_data=data,
            )

        return data

    # ------------------------------------------------------------------
    # User endpoints
    # ------------------------------------------------------------------

    def check_user(self, ic_no: str) -> dict:
        """
        GET /api/v1/obs/{ic_no}
        Returns Check User object: ic_no, name, email, mobile_no, result
        result: REGISTERED_USER | USER_NOT_REGISTERED
        """
        return self._get(f'/api/v1/obs/{ic_no}')

    def register_user(self, ic_type: str, ic_no: str, name: str,
                      email: str, mobile_no: str) -> dict:
        """
        POST /api/v1/obs
        Registers a gig worker as a PRIHATIN user.
        ic_type: 'B' (new IC) | 'L' (old IC) | 'PR' (permanent resident)
        mobile_no must include country code: '601XXXXXXXX'
        Returns User Details object.
        """
        return self._post('/api/v1/obs', {
            'ic_type': ic_type,
            'ic_no': ic_no,
            'name': name,
            'email': email,
            'mobile_no': mobile_no,
        })

    def update_user(self, ic_no: str, gender: str, race: str,
                    person_status: str, nationality_id: str,
                    address_line_1: str, state_id: int, city_id: int,
                    post_code: str, next_of_kin_name: str,
                    next_of_kin_mobile_no: str, next_of_kin_relation: str,
                    address_line_2: str = None,
                    house_phone_no: str = None) -> dict:
        """
        PATCH /api/v1/obs/{ic_no}
        Updates a gig worker's profile details in PRIHATIN.
        """
        payload = {
            'gender': gender,
            'race': race,
            'person_status': person_status,
            'nationality_id': nationality_id,
            'address_line_1': address_line_1,
            'state_id': state_id,
            'city_id': city_id,
            'post_code': post_code,
            'next_of_kin_name': next_of_kin_name,
            'next_of_kin_mobile_no': next_of_kin_mobile_no,
            'next_of_kin_relation': next_of_kin_relation,
        }
        if address_line_2:
            payload['address_line_2'] = address_line_2
        if house_phone_no:
            payload['house_phone_no'] = house_phone_no
        return self._patch(f'/api/v1/obs/{ic_no}', payload)

    def get_contribution_list(self, ic_no: str) -> dict:
        """
        GET /api/v1/obs/{ic_no}/contributions
        Returns paginated active contributions for a gig worker.
        """
        return self._get(f'/api/v1/obs/{ic_no}/contributions')

    # ------------------------------------------------------------------
    # Deduction endpoints
    # ------------------------------------------------------------------

    def submit_deduction(self, request_id: str, deductions: list[dict]) -> dict:
        """
        POST /api/v1/deductions
        Submit deduction records for one or more gig workers.
        Response is 202 Accepted (async); final result comes via callback.

        Each deduction dict must contain:
          ic_no, transaction_id, transacted_at ('YYYY-MM-DD HH:MM:SS'),
          sector_code, amount (the deduction amount, >= 0),
          start_point_latitude, start_point_longitude,
          end_point_latitude, end_point_longitude
        """
        return self._post('/api/v1/deductions', {
            'request_id': request_id,
            'deductions': deductions,
        })

    def cancel_deduction(self, transaction_id: str) -> dict:
        """
        PUT /api/v1/deductions/{transaction_id}
        Cancel a previously submitted deduction.
        """
        return self._put(f'/api/v1/deductions/{transaction_id}')

    # ------------------------------------------------------------------
    # Reference data endpoints
    # ------------------------------------------------------------------

    def get_sectors(self) -> dict:
        """GET /api/v1/sectors — paginated list of sectors with class codes."""
        return self._get('/api/v1/sectors')

    def get_states(self) -> dict:
        """GET /api/v1/states — paginated list of states and their cities."""
        return self._get('/api/v1/states')

    # ------------------------------------------------------------------
    # Batch endpoints
    # ------------------------------------------------------------------

    def batch_check_users(self, ic_numbers: list[str]) -> dict:
        """
        GET /api/v1/check-ic?ic_no={comma-separated ICs}
        Check registration status for multiple IC numbers at once.
        """
        return self._get('/api/v1/check-ic', params={'ic_no': ','.join(ic_numbers)})

    def batch_register_users(self, users: list[dict]) -> dict:
        """
        POST /api/v1/signup
        Register multiple gig workers in one request.
        Each user dict: ic_type, ic_no, name, email, mobile_no
        Response contains per-user success/fail results (async via callback).
        """
        return self._post('/api/v1/signup', {'users': users})

    def batch_update_users(self, users: list[dict]) -> dict:
        """
        PATCH /api/v1/user-details
        Update profile details for multiple gig workers at once.
        """
        return self._post('/api/v1/user-details', {'users': users})

    # ------------------------------------------------------------------
    # Convenience helpers used by GigHala
    # ------------------------------------------------------------------

    def ensure_user_registered(self, user) -> bool:
        """
        Check whether a User is registered with PERKESO and register them if not.
        Returns True if the user is (now) registered, False if registration failed
        or credentials are not configured.

        `user` is a GigHala User model instance. Required fields:
          ic_number, name, email, phone (or mobile_no)
        """
        if not self._is_configured():
            logger.warning('PERKESO credentials not configured; skipping registration')
            return False

        ic_no = (user.ic_number or '').strip()
        if not ic_no:
            logger.warning('User %d has no IC number; cannot register with PERKESO', user.id)
            return False

        try:
            result = self.check_user(ic_no)
            if result.get('data', {}).get('result') == 'REGISTERED_USER':
                return True

            # Not yet registered — register them now
            mobile_no = (getattr(user, 'phone', None) or '').strip()
            if mobile_no and not mobile_no.startswith('60'):
                mobile_no = '60' + mobile_no.lstrip('0')

            ic_type = (getattr(user, 'ic_type', None) or 'B')
            if ic_type not in ('B', 'L', 'PR'):
                ic_type = 'B'

            self.register_user(
                ic_type=ic_type,
                ic_no=ic_no,
                name=user.name or user.username or '',
                email=user.email or '',
                mobile_no=mobile_no,
            )
            logger.info('Registered user %d with PERKESO', user.id)
            return True

        except PERKESOError as exc:
            # Already registered via another platform — treat as success
            if exc.status_code == 422:
                response = exc.response_data or {}
                data = response.get('data', {})
                if 'ic_no' in data:
                    return True
            logger.error('PERKESO registration failed for user %d: %s', user.id, exc)
            return False
        except Exception as exc:
            logger.error('Unexpected error registering user %d with PERKESO: %s', user.id, exc)
            return False

    def submit_job_deduction(self, contribution, user, gig,
                              lat: float = 3.1390, lng: float = 101.6869) -> dict | None:
        """
        Submit a single deduction for a completed gig job.

        `contribution` — SocsoContribution model instance
        `user`         — freelancer User model instance
        `gig`          — Gig model instance
        `lat`/`lng`    — worker location (defaults to KL centre for remote gigs)

        Returns the PERKESO API response dict, or None if not configured.
        """
        if not self._is_configured():
            return None

        ic_no = (user.ic_number or '').strip()
        if not ic_no:
            logger.warning('Cannot submit PERKESO deduction: user %d has no IC', user.id)
            return None

        sector_code = (getattr(user, 'perkeso_sector_code', None)
                       or DEFAULT_SECTOR_CODE)

        # Use gig location if available, else default to KL
        start_lat = getattr(gig, 'latitude', None) or lat
        start_lng = getattr(gig, 'longitude', None) or lng

        transacted_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

        # perkeso_request_id is a UUID set before the DB row is committed,
        # so it is always available here and matches the callback lookup key.
        request_id = contribution.perkeso_request_id

        try:
            result = self.submit_deduction(
                request_id=request_id,
                deductions=[{
                    'ic_no': ic_no,
                    'transaction_id': request_id,
                    'transacted_at': transacted_at,
                    'sector_code': sector_code,
                    'amount': round(contribution.socso_amount, 2),
                    'start_point_latitude': float(start_lat),
                    'start_point_longitude': float(start_lng),
                    'end_point_latitude': float(start_lat),
                    'end_point_longitude': float(start_lng),
                }],
            )
            logger.info(
                'PERKESO deduction submitted: request_id=%s user=%d amount=RM%.2f',
                request_id, user.id, contribution.socso_amount,
            )
            return result
        except PERKESOError as exc:
            logger.error(
                'PERKESO deduction failed for contribution %d: %s', contribution.id, exc
            )
            return None
        except Exception as exc:
            logger.error(
                'Unexpected error submitting PERKESO deduction for contribution %d: %s',
                contribution.id, exc,
            )
            return None
