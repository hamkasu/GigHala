package com.gighala.app.plugins;

import android.content.Context;
import androidx.biometric.BiometricManager;
import androidx.biometric.BiometricPrompt;
import androidx.core.content.ContextCompat;
import androidx.fragment.app.FragmentActivity;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import java.util.concurrent.Executor;

@CapacitorPlugin(name = "GigHalaBiometric")
public class BiometricPlugin extends Plugin {

    @PluginMethod
    public void isAvailable(PluginCall call) {
        Context context = getContext();
        BiometricManager biometricManager = BiometricManager.from(context);
        JSObject result = new JSObject();

        int canAuthenticate = biometricManager.canAuthenticate(
            BiometricManager.Authenticators.BIOMETRIC_STRONG |
            BiometricManager.Authenticators.DEVICE_CREDENTIAL
        );

        switch (canAuthenticate) {
            case BiometricManager.BIOMETRIC_SUCCESS:
                result.put("isAvailable", true);
                result.put("biometryType", getBiometryType(context));
                call.resolve(result);
                break;
            case BiometricManager.BIOMETRIC_ERROR_NO_HARDWARE:
                result.put("isAvailable", false);
                result.put("error", "NO_HARDWARE");
                call.resolve(result);
                break;
            case BiometricManager.BIOMETRIC_ERROR_HW_UNAVAILABLE:
                result.put("isAvailable", false);
                result.put("error", "HW_UNAVAILABLE");
                call.resolve(result);
                break;
            case BiometricManager.BIOMETRIC_ERROR_NONE_ENROLLED:
                result.put("isAvailable", false);
                result.put("error", "NONE_ENROLLED");
                call.resolve(result);
                break;
            default:
                result.put("isAvailable", false);
                result.put("error", "UNKNOWN");
                call.resolve(result);
        }
    }

    @PluginMethod
    public void authenticate(PluginCall call) {
        String title = call.getString("title", "GigHala");
        String subtitle = call.getString("subtitle", "Log masuk dengan biometrik");
        String description = call.getString("description", "Sahkan identiti anda");
        String cancelTitle = call.getString("cancelTitle", "Batal");

        FragmentActivity activity = getActivity();
        Executor executor = ContextCompat.getMainExecutor(activity);

        BiometricPrompt.AuthenticationCallback callback =
            new BiometricPrompt.AuthenticationCallback() {
                @Override
                public void onAuthenticationSucceeded(
                    BiometricPrompt.AuthenticationResult result) {
                    super.onAuthenticationSucceeded(result);
                    JSObject ret = new JSObject();
                    ret.put("verified", true);
                    call.resolve(ret);
                }

                @Override
                public void onAuthenticationError(int errorCode, CharSequence errString) {
                    super.onAuthenticationError(errorCode, errString);
                    JSObject ret = new JSObject();
                    ret.put("verified", false);
                    ret.put("errorCode", errorCode);
                    ret.put("errorMessage", errString.toString());
                    call.reject(errString.toString(), String.valueOf(errorCode), null, ret);
                }

                @Override
                public void onAuthenticationFailed() {
                    super.onAuthenticationFailed();
                    // Don't reject here — user can retry
                }
            };

        BiometricPrompt biometricPrompt = new BiometricPrompt(activity, executor, callback);

        BiometricPrompt.PromptInfo promptInfo = new BiometricPrompt.PromptInfo.Builder()
            .setTitle(title)
            .setSubtitle(subtitle)
            .setDescription(description)
            .setNegativeButtonText(cancelTitle)
            .setAllowedAuthenticators(BiometricManager.Authenticators.BIOMETRIC_STRONG)
            .build();

        activity.runOnUiThread(() -> biometricPrompt.authenticate(promptInfo));
    }

    private String getBiometryType(Context context) {
        BiometricManager manager = BiometricManager.from(context);
        if (manager.canAuthenticate(BiometricManager.Authenticators.BIOMETRIC_STRONG)
                == BiometricManager.BIOMETRIC_SUCCESS) {
            // Distinguish fingerprint vs face (best effort)
            return "touchId"; // Default; face detection requires additional API
        }
        return "none";
    }
}
