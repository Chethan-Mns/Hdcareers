package `in`.hdcareers.admin

import android.Manifest
import android.content.Intent
import android.os.Build
import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import androidx.core.view.WindowCompat
import androidx.core.app.ActivityCompat
import android.content.pm.PackageManager
import androidx.fragment.app.FragmentActivity
import androidx.lifecycle.viewmodel.compose.viewModel

class MainActivity:FragmentActivity() {
    private lateinit var vm: AdminViewModel

    override fun onCreate(savedInstanceState:Bundle?) {
        super.onCreate(savedInstanceState)
        WindowCompat.getInsetsController(window,window.decorView).isAppearanceLightStatusBars = true
        setContent {
            vm=viewModel()
            if(intent?.getBooleanExtra("open_review",false)==true) vm.tab=1
            PremiumAdminRoot(vm,
                onBiometricSignIn={authenticate { vm.biometricSignIn() }},
                onEnableBiometric={authenticate { vm.enableBiometric() }},
                onRequestNotificationPermission={
                    requestNotificationPermission()
                })
        }
    }
    override fun onNewIntent(intent:Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        if(intent.getBooleanExtra("open_review",false) && ::vm.isInitialized) vm.tab=1
    }
    private fun requestNotificationPermission() {
        if(Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this,arrayOf(Manifest.permission.POST_NOTIFICATIONS),1001)
        }
    }

    private fun authenticate(onSuccess:()->Unit) {
        val available=BiometricManager.from(this).canAuthenticate(
            BiometricManager.Authenticators.BIOMETRIC_STRONG or BiometricManager.Authenticators.DEVICE_CREDENTIAL)
        if(available!=BiometricManager.BIOMETRIC_SUCCESS) {
            if(::vm.isInitialized) vm.message="Set up fingerprint or screen lock in Android Settings first."
            return
        }
        val prompt=BiometricPrompt(this,ContextCompat.getMainExecutor(this),
            object:BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result:BiometricPrompt.AuthenticationResult) { onSuccess() }
                override fun onAuthenticationError(errorCode:Int,errString:CharSequence) {
                    if(::vm.isInitialized) vm.message=errString.toString()
                }
            })
        val info=BiometricPrompt.PromptInfo.Builder()
            .setTitle("HD Careers Admin")
            .setSubtitle("Confirm your identity to access private admin credentials")
            .setAllowedAuthenticators(BiometricManager.Authenticators.BIOMETRIC_STRONG or
                BiometricManager.Authenticators.DEVICE_CREDENTIAL).build()
        prompt.authenticate(info)
    }
}
