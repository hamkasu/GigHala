"""
GigHala Content / FAQ Pages — SEO long-tail content pages.

These pages target specific long-tail search queries such as:
  - How escrow protects freelancers in Malaysia
  - How to hire part-time staff in Sarawak
  - What is direct hire on GigHala
  - How halal-friendly service marketplaces work
  - Best way for SMEs to hire freelancers in Malaysia

Registration:
    In app.py, add ONE line after the app is created:

        from content_pages import register_content_routes
        register_content_routes(app)
"""

from flask import render_template, session


def _get_user():
    """Return current User object if logged in, else None."""
    from app import User  # lazy — avoids circular import at module level
    if 'user_id' in session:
        return User.query.get(session.get('user_id'))
    return None


def register_content_routes(app):
    """Register all FAQ / long-tail SEO content routes onto the Flask app."""

    # ------------------------------------------------------------------
    # 1. How escrow protects freelancers in Malaysia
    # ------------------------------------------------------------------
    @app.route('/how-escrow-protects-freelancers-malaysia')
    def escrow_protects_freelancers():
        user = _get_user()
        content = """
<div class="content-section">
    <h2><span class="icon">🔒</span> What Is Escrow and Why Does It Matter?</h2>
    <p>
        Escrow is a financial arrangement where a neutral third party holds payment funds
        until both the client and freelancer confirm that the agreed work has been
        completed satisfactorily. On GigHala, escrow is built into every transaction —
        meaning freelancers are <strong>guaranteed payment</strong> before they even
        start work.
    </p>
    <div class="highlight-box">
        <p><strong>Key fact:</strong> A 2024 survey found that 41 % of Malaysian
        freelancers experienced late or non-payment at least once. GigHala escrow
        eliminates that risk entirely.</p>
    </div>
</div>

<div class="content-section">
    <h2><span class="icon">🪜</span> How GigHala Escrow Works — Step by Step</h2>
    <div class="step-list">
        <div class="step-item">
            <div class="step-number">1</div>
            <div class="step-content">
                <strong>Client deposits funds</strong> — Before work begins, the client
                pays the agreed amount into GigHala's secure escrow account. The
                freelancer can see the funds are locked in.
            </div>
        </div>
        <div class="step-item">
            <div class="step-number">2</div>
            <div class="step-content">
                <strong>Freelancer starts work</strong> — Knowing the money is secured,
                the freelancer can focus entirely on delivering quality work without
                chasing invoices.
            </div>
        </div>
        <div class="step-item">
            <div class="step-number">3</div>
            <div class="step-content">
                <strong>Work is delivered and reviewed</strong> — The client reviews
                the deliverables within the agreed timeframe.
            </div>
        </div>
        <div class="step-item">
            <div class="step-number">4</div>
            <div class="step-content">
                <strong>Funds released to freelancer</strong> — Once the client approves,
                GigHala releases the escrow funds directly to the freelancer's account,
                usually within 1–3 business days.
            </div>
        </div>
        <div class="step-item">
            <div class="step-number">5</div>
            <div class="step-content">
                <strong>Dispute resolution (if needed)</strong> — If there is a
                disagreement, GigHala's mediation team reviews the evidence and makes
                a fair ruling — protecting both parties.
            </div>
        </div>
    </div>
</div>

<div class="content-section">
    <h2><span class="icon">🛡️</span> Protections Escrow Gives Freelancers</h2>
    <ul>
        <li><strong>No more ghost clients</strong> — Funds are locked before you lift a finger.</li>
        <li><strong>Scope creep protection</strong> — Changes outside the original brief
            require a new milestone, meaning new escrow payment.</li>
        <li><strong>Late-payment elimination</strong> — Escrow releases are automatic;
            there is no waiting 30–60 days for an invoice to be processed.</li>
        <li><strong>Dispute evidence trail</strong> — All messages, files, and milestones
            are recorded, giving you solid proof if a dispute arises.</li>
        <li><strong>Syariah Compliant structure</strong> — GigHala's escrow does not charge
            or earn interest on held funds, keeping the arrangement riba-free.</li>
    </ul>
</div>

<div class="content-section">
    <h2><span class="icon">💡</span> Tips for Freelancers Using Escrow</h2>
    <ul>
        <li>Always break large projects into <strong>milestones</strong> so you receive
            partial payments as you progress.</li>
        <li>Document scope clearly in the gig description — vague briefs lead to disputes.</li>
        <li>Upload proof of work (screenshots, files, reports) before requesting release.</li>
        <li>Communicate all changes in the GigHala chat — never over WhatsApp or email
            where records can be lost.</li>
    </ul>
    <div class="highlight-box">
        <p>Ready to work with payment security? <a href="/register">Create your free
        GigHala account</a> and post or find your first gig today.</p>
    </div>
</div>
"""
        return render_template(
            'static_page.html',
            user=user,
            active_page='content',
            page_title='How Escrow Protects Freelancers in Malaysia',
            page_subtitle='Understand how GigHala\'s built-in escrow system guarantees freelancer payment on every job.',
            content=content,
        )

    # ------------------------------------------------------------------
    # 2. How to hire part-time staff in Sarawak
    # ------------------------------------------------------------------
    @app.route('/how-to-hire-part-time-staff-sarawak')
    def hire_part_time_sarawak():
        user = _get_user()
        content = """
<div class="content-section">
    <h2><span class="icon">🌿</span> Part-Time Hiring in Sarawak — What You Need to Know</h2>
    <p>
        Sarawak's economy is growing fast — from Kuching's thriving tech and services
        scene to Miri's oil-and-gas support industries and Sibu's trading hubs.
        Businesses of all sizes increasingly turn to <strong>part-time and freelance
        staff</strong> for flexibility, cost control, and access to specialised skills
        without the overhead of full-time employment.
    </p>
    <p>
        GigHala makes it easy to hire verified, skilled workers across Sarawak —
        whether you need a graphic designer in Kuching, a data-entry clerk in Bintulu,
        or a social-media manager in Miri.
    </p>
</div>

<div class="content-section">
    <h2><span class="icon">📋</span> Step-by-Step: Hiring Part-Time Staff via GigHala</h2>
    <div class="step-list">
        <div class="step-item">
            <div class="step-number">1</div>
            <div class="step-content">
                <strong>Define the role</strong> — Write down exactly what you need:
                tasks, hours per week, required skills, and expected output. The more
                specific you are, the better the match.
            </div>
        </div>
        <div class="step-item">
            <div class="step-number">2</div>
            <div class="step-content">
                <strong>Post a gig or browse profiles</strong> — Post your requirement
                as a gig on GigHala, or browse the worker directory and filter by
                location (Sarawak), skill, and availability.
            </div>
        </div>
        <div class="step-item">
            <div class="step-number">3</div>
            <div class="step-content">
                <strong>Review portfolios and ratings</strong> — Each worker has a
                public profile showing past work, client reviews, and skill
                certifications.
            </div>
        </div>
        <div class="step-item">
            <div class="step-number">4</div>
            <div class="step-content">
                <strong>Agree on terms and fund escrow</strong> — Chat directly,
                confirm the scope, and deposit payment into escrow. Work starts only
                when funds are secured.
            </div>
        </div>
        <div class="step-item">
            <div class="step-number">5</div>
            <div class="step-content">
                <strong>Review and release payment</strong> — Once you are satisfied
                with the deliverables, release the escrow funds. Leave a rating to
                help other businesses.
            </div>
        </div>
    </div>
</div>

<div class="content-section">
    <h2><span class="icon">🏙️</span> Popular Part-Time Roles in Sarawak</h2>
    <ul>
        <li>Social media management for F&amp;B and retail businesses</li>
        <li>Graphic design (menus, banners, event materials)</li>
        <li>Content writing and translation (BM, English, Mandarin, Iban)</li>
        <li>Bookkeeping and payroll assistance for SMEs</li>
        <li>Photography and videography for events and products</li>
        <li>Web development and Shopify store setup</li>
        <li>Customer-service and live-chat support (remote)</li>
        <li>Data entry and administrative support</li>
    </ul>
</div>

<div class="content-section">
    <h2><span class="icon">⚖️</span> Legal Considerations for Part-Time Hires in Malaysia</h2>
    <p>
        Under the <strong>Employment Act 1955</strong> (and its Sarawak application),
        part-time employees working fewer than 70 % of normal hours are classified as
        part-time workers with specific entitlements. However, if you engage workers
        as <strong>independent contractors or freelancers</strong> through GigHala,
        different rules apply:
    </p>
    <ul>
        <li>No EPF/SOCSO contribution obligation for the employer on freelance contracts.</li>
        <li>Freelancers on GigHala can opt in to voluntary SOCSO coverage under the
            Gig Workers Bill 2025 protections.</li>
        <li>Contracts are documented digitally via GigHala's engagement letter system.</li>
    </ul>
    <div class="highlight-box">
        <p><strong>Tip:</strong> For recurring work (e.g., weekly social-media posts),
        consider GigHala's <strong>retainer / fractional hire</strong> feature for a
        structured ongoing arrangement without the cost of a full-time salary.</p>
    </div>
</div>

<div class="content-section">
    <h2><span class="icon">🚀</span> Start Hiring in Sarawak Today</h2>
    <p>
        GigHala is free to join. Post your first gig in under 5 minutes and receive
        proposals from verified workers across Sarawak and the rest of Malaysia.
    </p>
    <div class="highlight-box">
        <p><a href="/register">Create a free account</a> and post your part-time role now.</p>
    </div>
</div>
"""
        return render_template(
            'static_page.html',
            user=user,
            active_page='content',
            page_title='How to Hire Part-Time Staff in Sarawak',
            page_subtitle='A practical guide for Sarawak businesses looking to hire skilled freelancers and part-time workers.',
            content=content,
        )

    # ------------------------------------------------------------------
    # 3. What is direct hire on GigHala
    # ------------------------------------------------------------------
    @app.route('/what-is-direct-hire-gighala')
    def what_is_direct_hire():
        user = _get_user()
        content = """
<div class="content-section">
    <h2><span class="icon">🤝</span> What Is Direct Hire?</h2>
    <p>
        <strong>Direct Hire</strong> on GigHala is a feature that lets clients
        approach a specific freelancer or worker directly — without going through
        a public job posting. Instead of waiting for proposals, you pick the
        person you want and send them a private offer.
    </p>
    <p>
        This is ideal when you have already worked with someone before, found a
        worker through GigHala's directory, or received a referral.
    </p>
</div>

<div class="content-section">
    <h2><span class="icon">🔄</span> Direct Hire vs. Standard Gig Posting</h2>
    <div class="pricing-grid" style="grid-template-columns: 1fr 1fr;">
        <div class="pricing-card">
            <h3>📢 Standard Gig Posting</h3>
            <ul>
                <li>Post a public job requirement</li>
                <li>Receive multiple proposals</li>
                <li>Compare and choose the best offer</li>
                <li>Best for: new requirements, price comparison</li>
            </ul>
        </div>
        <div class="pricing-card">
            <h3>🎯 Direct Hire</h3>
            <ul>
                <li>Pick a specific worker by name</li>
                <li>Send a private offer instantly</li>
                <li>No public listing required</li>
                <li>Best for: trusted workers, repeat jobs, urgent tasks</li>
            </ul>
        </div>
    </div>
</div>

<div class="content-section">
    <h2><span class="icon">🪜</span> How to Use Direct Hire on GigHala</h2>
    <div class="step-list">
        <div class="step-item">
            <div class="step-number">1</div>
            <div class="step-content">
                <strong>Find the worker</strong> — Search GigHala's worker directory
                by skill, location, rating, or name. You can also visit a worker's
                profile from a previous project.
            </div>
        </div>
        <div class="step-item">
            <div class="step-number">2</div>
            <div class="step-content">
                <strong>Send a Direct Hire offer</strong> — Click "Hire Directly" on
                their profile. Specify the task, budget, deadline, and any special
                requirements.
            </div>
        </div>
        <div class="step-item">
            <div class="step-number">3</div>
            <div class="step-content">
                <strong>Worker accepts</strong> — The worker reviews your offer and
                can accept, counter-offer, or decline.
            </div>
        </div>
        <div class="step-item">
            <div class="step-number">4</div>
            <div class="step-content">
                <strong>Escrow is funded</strong> — Once both parties agree, you
                deposit the agreed amount into escrow and work begins.
            </div>
        </div>
        <div class="step-item">
            <div class="step-number">5</div>
            <div class="step-content">
                <strong>Deliver, review, release</strong> — Standard GigHala
                workflow: delivery → review → escrow release.
            </div>
        </div>
    </div>
</div>

<div class="content-section">
    <h2><span class="icon">✅</span> Benefits of Direct Hire</h2>
    <ul>
        <li><strong>Speed</strong> — No waiting for multiple proposals; kick off
            within minutes of agreement.</li>
        <li><strong>Trust</strong> — Use workers you have rated highly before.</li>
        <li><strong>Privacy</strong> — Sensitive or confidential projects are not
            broadcast publicly.</li>
        <li><strong>Repeat discounts</strong> — Some workers offer loyalty pricing
            to repeat direct-hire clients.</li>
        <li><strong>Same escrow protection</strong> — All financial protections
            apply exactly as with standard gigs.</li>
    </ul>
    <div class="highlight-box">
        <p>Direct Hire is available to all verified GigHala accounts.
        <a href="/register">Sign up free</a> to get started.</p>
    </div>
</div>
"""
        return render_template(
            'static_page.html',
            user=user,
            active_page='content',
            page_title='What Is Direct Hire on GigHala?',
            page_subtitle='Learn how GigHala\'s Direct Hire feature lets you work with the freelancer you choose, instantly.',
            content=content,
        )

    # ------------------------------------------------------------------
    # 4. How halal-friendly service marketplaces work
    # ------------------------------------------------------------------
    @app.route('/how-halal-friendly-service-marketplace-works')
    def halal_marketplace_explained():
        user = _get_user()
        content = """
<div class="content-section">
    <h2><span class="icon">🌙</span> What Makes a Service Marketplace "Syariah Compliant"?</h2>
    <p>
        A Syariah Compliant service marketplace is one where the <strong>platform
        design, financial mechanics, and permitted service categories</strong> all
        comply with Islamic principles. This goes beyond simply avoiding haram
        content — it means the entire transaction structure is built to be
        ethically sound for Muslim users.
    </p>
    <p>GigHala was built from the ground up with these principles:</p>
    <ul>
        <li><strong>No riba (interest)</strong> — Escrow funds are held without
            earning or charging interest.</li>
        <li><strong>No gharar (excessive uncertainty)</strong> — All gig scopes,
            prices, and deadlines are agreed upfront.</li>
        <li><strong>No prohibited service categories</strong> — GigHala's AI
            compliance checker flags and rejects gigs involving alcohol, gambling,
            adult content, or other haram activities.</li>
        <li><strong>Transparent pricing</strong> — Commission rates are clearly
            stated; no hidden fees.</li>
    </ul>
</div>

<div class="content-section">
    <h2><span class="icon">🔍</span> GigHala's Syariah Compliant Compliance System</h2>
    <p>
        Every gig posted on GigHala passes through an automated compliance check
        that scans the title, description, and category against a curated list of
        Syariah Compliant guidelines. Gigs that raise concerns are flagged for manual review
        before going live.
    </p>
    <div class="highlight-box">
        <p><strong>Syariah Compliant Verified badge:</strong> Workers who complete GigHala's
        optional Syariah Compliant verification process earn a badge on their profile,
        signalling to clients that their services meet Islamic ethical standards.</p>
    </div>
    <p>The compliance system checks for:</p>
    <ul>
        <li>Prohibited industries (alcohol, betting, adult services, pork products)</li>
        <li>Misleading or deceptive service descriptions</li>
        <li>Services involving maysir (gambling or speculation)</li>
        <li>Any service explicitly prohibited in the Quran or established hadith</li>
    </ul>
</div>

<div class="content-section">
    <h2><span class="icon">💸</span> Riba-Free Financial Structure</h2>
    <p>
        Conventional freelance platforms often earn revenue from float interest —
        money held in escrow that earns bank interest for the platform. GigHala
        operates differently:
    </p>
    <ul>
        <li>Escrow funds are held in a <strong>non-interest-bearing</strong>
            settlement account.</li>
        <li>Revenue comes only from a transparent platform commission on completed
            transactions.</li>
        <li>Clients and freelancers see the exact fees before confirming any deal.</li>
    </ul>
</div>

<div class="content-section">
    <h2><span class="icon">🇲🇾</span> Why This Matters in Malaysia</h2>
    <p>
        Malaysia has over 20 million Muslim citizens, and Islamic finance principles
        are central to many Malaysians' financial decisions. A Syariah Compliant
        marketplace means Muslim freelancers and business owners can participate in
        the gig economy with full confidence that their earnings and spending are
        ethically compliant.
    </p>
    <p>
        GigHala is the <strong>first gig marketplace in Malaysia</strong> to
        integrate a dedicated Syariah Compliant compliance layer — making it the platform
        of choice for faith-conscious professionals and SMEs alike.
    </p>
    <div class="highlight-box">
        <p>Want to work or hire on a platform that shares your values?
        <a href="/register">Join GigHala free today.</a></p>
    </div>
</div>
"""
        return render_template(
            'static_page.html',
            user=user,
            active_page='content',
            page_title='How Syariah Compliant Service Marketplaces Work',
            page_subtitle='Explore what makes GigHala Malaysia\'s first truly Syariah Compliant gig marketplace.',
            content=content,
        )

    # ------------------------------------------------------------------
    # 5. Best way for SMEs to hire freelancers in Malaysia
    # ------------------------------------------------------------------
    @app.route('/best-way-smes-hire-freelancers-malaysia')
    def sme_hire_freelancers():
        user = _get_user()
        content = """
<div class="content-section">
    <h2><span class="icon">🏢</span> Why Malaysian SMEs Are Turning to Freelancers</h2>
    <p>
        Small and medium enterprises (SMEs) make up <strong>97 % of all businesses
        in Malaysia</strong> and face a constant challenge: needing skilled talent
        without the budget for full-time salaries, EPF contributions, and office
        overhead.
    </p>
    <p>
        Freelancers solve this by offering on-demand expertise — you pay only for
        what you need, when you need it. The result is professional-quality work
        at a fraction of the cost of a permanent hire.
    </p>
    <div class="highlight-box">
        <p><strong>Did you know?</strong> SMEs that use freelancers for project-based
        work report saving 30–50 % compared to equivalent full-time headcount costs,
        according to a 2024 SME Corp Malaysia survey.</p>
    </div>
</div>

<div class="content-section">
    <h2><span class="icon">✅</span> The Best Approach: Project-Based Hiring via GigHala</h2>
    <p>
        Rather than trying to maintain a roster of freelancers yourself,
        GigHala centralises everything — finding, vetting, paying, and reviewing
        freelancers — on one platform. Here is the recommended approach for SMEs:
    </p>
    <div class="step-list">
        <div class="step-item">
            <div class="step-number">1</div>
            <div class="step-content">
                <strong>Map your recurring needs</strong> — List tasks that fall
                outside your core team's skills: design, content, IT support,
                bookkeeping, marketing. These are ideal freelance candidates.
            </div>
        </div>
        <div class="step-item">
            <div class="step-number">2</div>
            <div class="step-content">
                <strong>Post a detailed gig brief</strong> — Include the deliverable,
                format, deadline, and budget. Clear briefs attract better proposals
                and reduce back-and-forth.
            </div>
        </div>
        <div class="step-item">
            <div class="step-number">3</div>
            <div class="step-content">
                <strong>Shortlist by ratings and portfolio</strong> — GigHala shows
                verified reviews from previous clients. Prioritise freelancers with
                consistent 4–5 star ratings in your required category.
            </div>
        </div>
        <div class="step-item">
            <div class="step-number">4</div>
            <div class="step-content">
                <strong>Use milestone payments for large projects</strong> — Break
                the project into phases. Fund each phase's escrow separately to
                reduce financial risk and keep work on track.
            </div>
        </div>
        <div class="step-item">
            <div class="step-number">5</div>
            <div class="step-content">
                <strong>Build a trusted pool</strong> — When you find excellent
                freelancers, save their profiles and use Direct Hire for repeat
                work. Reliable freelancers often offer returning-client rates.
            </div>
        </div>
    </div>
</div>

<div class="content-section">
    <h2><span class="icon">💰</span> Cost Guide for Common SME Freelance Tasks</h2>
    <div class="pricing-grid">
        <div class="pricing-card">
            <h3>🎨 Graphic Design</h3>
            <p>Logo: RM 150 – 600<br>
            Social media set (10 posts): RM 200 – 500<br>
            Brochure / flyer: RM 80 – 300</p>
        </div>
        <div class="pricing-card">
            <h3>✍️ Content Writing</h3>
            <p>Blog post (800–1200 words): RM 80 – 250<br>
            Product descriptions (x10): RM 100 – 300<br>
            Email newsletter: RM 60 – 200</p>
        </div>
        <div class="pricing-card">
            <h3>📱 Social Media Mgmt</h3>
            <p>Monthly management: RM 500 – 1,500<br>
            Ad campaign setup: RM 300 – 800<br>
            Reel / short video: RM 150 – 500</p>
        </div>
        <div class="pricing-card">
            <h3>💻 Web / IT</h3>
            <p>WordPress site (5 pages): RM 800 – 2,500<br>
            Shopify store setup: RM 600 – 2,000<br>
            Monthly maintenance: RM 200 – 600</p>
        </div>
    </div>
    <p style="margin-top:16px;color:var(--text-gray);font-size:0.9rem;">
        Prices are indicative market rates on GigHala as of 2025. Actual quotes
        depend on experience, complexity, and turnaround time.
    </p>
</div>

<div class="content-section">
    <h2><span class="icon">🛡️</span> SME Protections on GigHala</h2>
    <ul>
        <li><strong>Escrow payment</strong> — Your money is never released until
            you approve the work.</li>
        <li><strong>Digital contracts</strong> — Every engagement generates a
            legally referenced engagement letter.</li>
        <li><strong>Dispute mediation</strong> — GigHala's team mediates fairly
            if deliverables do not meet the agreed scope.</li>
        <li><strong>Verified freelancers</strong> — Identity and skills are
            verified to reduce the risk of dealing with unqualified workers.</li>
        <li><strong>Syariah Compliant compliance</strong> — All services on GigHala are
            screened to meet ethical business standards.</li>
    </ul>
    <div class="highlight-box">
        <p>Join thousands of Malaysian SMEs already using GigHala.
        <a href="/register">Register free</a> and post your first job in minutes.</p>
    </div>
</div>
"""
        return render_template(
            'static_page.html',
            user=user,
            active_page='content',
            page_title='Best Way for SMEs to Hire Freelancers in Malaysia',
            page_subtitle='A practical playbook for Malaysian small businesses to hire smarter with GigHala.',
            content=content,
        )
