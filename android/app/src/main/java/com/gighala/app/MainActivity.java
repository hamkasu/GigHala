package com.gighala.app;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;
import com.gighala.app.plugins.BiometricPlugin;

public class MainActivity extends BridgeActivity {

    @Override
    public void onCreate(Bundle savedInstanceState) {
        // Register custom plugins before super.onCreate
        registerPlugin(BiometricPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
