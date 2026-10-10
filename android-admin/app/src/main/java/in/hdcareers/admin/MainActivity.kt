package in.hdcareers.admin

import android.Manifest
import android.content.Intent
import android.os.Build
import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
import androidx.lifecycle.viewmodel.compose.viewModel

class MainActivity:FragmentActivity() {
    private val permission = registerForActivityResult(ActivityResultContracts.RequestPermission()) { }
    private lateinit var vm: AdminViewModel

    override fun onCreate(savedInstanceState:Bundle?) {
        super.onCreate(savedInstanceState)
        if(Build.VERSION.SDK_INT >= 33) permission.launch(Manifest.permission.POST_NOTIFICATIONS)
        setContent {
            vm=viewModel()
            if(intent?.getBooleanExtra("open_review",false)==true) vm.tab=1
            AdminRoot(vm,
                onBiometricSignIn={authenticate { vm.biometricSignIn() }},
                onEnableBiometric={authenticate { vm.enableBiometric() }},
                onRequestNotificationPermission={
                    if(Build.VERSION.SDK_INT>=33) permission.launch(Manifest.permission.POST_NOTIFICATIONS)
                })
        }
    }
    override fun onNewIntent(intent:Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        if(intent.getBooleanExtra("open_review",false) && ::vm.isInitialized) vm.tab=1
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
