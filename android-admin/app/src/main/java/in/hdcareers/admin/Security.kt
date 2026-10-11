package `in`.hdcareers.admin

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.nio.charset.StandardCharsets
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

class CredentialVault(private val context: Context) {
    private val prefs=context.getSharedPreferences("hd_secure",Context.MODE_PRIVATE)
    private val alias="in.hdcareers.admin.biometric.v1"

    private fun secret():SecretKey {
        val store=KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (store.getKey(alias,null) as? SecretKey)?.let { return it }
        val generator=KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore")
        generator.init(KeyGenParameterSpec.Builder(alias,KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setUserAuthenticationRequired(true)
            .setUserAuthenticationParameters(30,KeyProperties.AUTH_BIOMETRIC_STRONG or KeyProperties.AUTH_DEVICE_CREDENTIAL)
            .build())
        return generator.generateKey()
    }
    val exists:Boolean get()=prefs.contains("ciphertext")&&prefs.contains("iv")
    fun save(username:String,password:String) {
        val cipher=Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE,secret())
        val raw=(username+"\n"+password).toByteArray(StandardCharsets.UTF_8)
        prefs.edit().putString("iv",Base64.encodeToString(cipher.iv,Base64.NO_WRAP))
            .putString("ciphertext",Base64.encodeToString(cipher.doFinal(raw),Base64.NO_WRAP)).apply()
    }
    fun read():Pair<String,String> {
        val iv=Base64.decode(prefs.getString("iv",""),Base64.NO_WRAP)
        val data=Base64.decode(prefs.getString("ciphertext",""),Base64.NO_WRAP)
        val cipher=Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE,secret(),GCMParameterSpec(128,iv))
        val raw=String(cipher.doFinal(data),StandardCharsets.UTF_8)
        val idx=raw.indexOf('\n')
        require(idx>0) { "Saved credentials are invalid." }
        return raw.substring(0,idx) to raw.substring(idx+1)
    }
    fun clear() { prefs.edit().remove("ciphertext").remove("iv").apply() }
}
