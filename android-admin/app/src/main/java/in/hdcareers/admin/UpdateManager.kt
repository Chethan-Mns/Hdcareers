package `in`.hdcareers.admin

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.core.content.FileProvider
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.io.File
import java.security.MessageDigest
import java.util.concurrent.TimeUnit

data class AvailableUpdate(val code:Int,val name:String,val url:String,val sha:String,val notes:String)

object UpdateManager {
    private val client=OkHttpClient.Builder().connectTimeout(15,TimeUnit.SECONDS)
        .readTimeout(90,TimeUnit.SECONDS).followRedirects(true).build()

    fun parse(json:JSONObject):AvailableUpdate? {
        if(!json.optBoolean("available"))return null
        val code=json.optInt("versionCode")
        val sha=json.optString("sha256").lowercase()
        val url=json.optString("apkUrl")
        if(code<=BuildConfig.VERSION_CODE||!url.startsWith("https://")||!Regex("[0-9a-f]{64}").matches(sha))
            return null
        return AvailableUpdate(code,json.optString("versionName"),url,sha,json.optString("notes"))
    }

    suspend fun download(context:Context,update:AvailableUpdate):File=withContext(Dispatchers.IO) {
        val directory=File(context.cacheDir,"updates").apply { mkdirs() }
        val target=File(directory,"hdcareers-update.apk")
        val temp=File(directory,"hdcareers-update.part")
        try {
            val request=Request.Builder().url(update.url).get().build()
            client.newCall(request).execute().use { response ->
                if(!response.isSuccessful)error("Update download failed: HTTP ${response.code}")
                val body=response.body ?: error("Update is empty")
                val digest=MessageDigest.getInstance("SHA-256")
                body.byteStream().use { input ->
                    temp.outputStream().use { output ->
                        val buf=ByteArray(65536)
                        while(true){
                            val count=input.read(buf)
                            if(count<0)break
                            digest.update(buf,0,count)
                            output.write(buf,0,count)
                        }
                    }
                }
                val found=digest.digest().joinToString("") { "%02x".format(it) }
                check(found.equals(update.sha,true)) { "Update checksum mismatch" }
                check(temp.length()>0) { "Update download was empty" }
                if(target.exists())target.delete()
                check(temp.renameTo(target)) { "Could not save update" }
            }
            target
        } finally { temp.delete() }
    }

    fun install(context:Context,file:File){
        val uri=FileProvider.getUriForFile(context,"${context.packageName}.updates",file)
        val intent=Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(uri,"application/vnd.android.package-archive")
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        context.startActivity(intent)
    }
}
