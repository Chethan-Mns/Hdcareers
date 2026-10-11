package `in`.hdcareers.admin

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.Cookie
import okhttp3.CookieJar
import okhttp3.HttpUrl
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

class AdminApi {
    private val cookies = mutableListOf<Cookie>()
    private val cookieJar = object : CookieJar {
        override fun saveFromResponse(url: HttpUrl, cookiesNew: List<Cookie>) {
            synchronized(cookies) {
                for(c in cookiesNew) {
                    cookies.removeAll { it.name == c.name && it.domain == c.domain }
                    if (c.expiresAt > System.currentTimeMillis()) cookies.add(c)
                }
            }
        }
        override fun loadForRequest(url: HttpUrl): List<Cookie> =
            synchronized(cookies) { cookies.filter { it.matches(url) && it.expiresAt > System.currentTimeMillis() } }
    }
    private val client = OkHttpClient.Builder().cookieJar(cookieJar)
        .connectTimeout(15, TimeUnit.SECONDS).readTimeout(35, TimeUnit.SECONDS).build()
    private val type = "application/json; charset=utf-8".toMediaType()
    private val host = "https://hdcareers.in"

    private suspend fun request(path: String, body: JSONObject? = null): String = withContext(Dispatchers.IO) {
        val builder = Request.Builder().url(host + path).header("Accept","application/json")
        if(body != null) builder.post(body.toString().toRequestBody(type))
        client.newCall(builder.build()).execute().use { response ->
            val value = response.body?.string().orEmpty()
            if (!response.isSuccessful) {
                val msg=runCatching { JSONObject(value).optString("error") }.getOrNull().orEmpty()
                throw IOException(msg.ifBlank { "Server returned HTTP ${response.code}" })
            }
            value
        }
    }
    suspend fun login(username: String, password: String) {
        val result = JSONObject(request("/api/admin/login",JSONObject()
            .put("username",username).put("password",password)))
        if (!result.optBoolean("authenticated")) throw IOException("Sign-in failed.")
    }
    suspend fun logout() {
        runCatching { request("/api/admin/logout",JSONObject()) }
        synchronized(cookies) { cookies.clear() }
    }
    suspend fun batch(): DailyBatch = parseBatch(JSONObject(request("/api/admin/daily-batch")))
    suspend fun jobs():List<Job> = parseJobs(JSONArray(request("/data/jobs.json")))
    suspend fun logoSources():Map<String,CompanyLogoSource> = parseCompanyLogoSources(
        JSONObject(request("/data/company-logos.json")),
        JSONObject(request("/data/company-logo-domains.json"))
    )
    suspend fun traffic(days: Int):Traffic = parseTraffic(JSONObject(request("/api/admin/traffic?days=$days")))
    suspend fun checker():JSONObject = JSONObject(request("/api/admin/availability"))
    suspend fun automation():JSONObject = JSONObject(request("/data/automation-status.json"))
    suspend fun updateReview(batch:String,id:String,status:String):DailyBatch =
        parseBatch(JSONObject(request("/api/admin/daily-batch",JSONObject().put("action","review")
            .put("batchId",batch).put("candidateId",id).put("decision",status))))
    suspend fun swap(batch:String,priority:String,backup:String):DailyBatch =
        parseBatch(JSONObject(request("/api/admin/daily-batch",JSONObject().put("action","swap")
            .put("batchId",batch).put("priorityId",priority).put("backupId",backup))))
    suspend fun submit(batch:DailyBatch):String {
        val jobs=JSONArray()
        batch.priority.forEach { jobs.put(it.job ?: throw IOException("Missing verified job details")) }
        val result=JSONObject(request("/api/admin/publish",JSONObject().put("jobs",jobs)))
        if(!result.optBoolean("queued")) throw IOException("Publisher did not accept the batch.")
        return result.optString("message","Publishing requested. Check the deployment status.")
    }
    suspend fun markSubmitted(batch:String):DailyBatch =
        parseBatch(JSONObject(request("/api/admin/daily-batch",JSONObject().put("action","submitted").put("batchId",batch))))
    suspend fun extractJob(url:String):JSONObject {
        val result=JSONObject(request("/api/admin/extract-job",JSONObject().put("url",url)))
        return result.optJSONObject("data") ?: throw IOException(result.optString("error","Job extraction failed."))
    }
    suspend fun publishOne(job:JSONObject):String {
        val result=JSONObject(request("/api/admin/publish",JSONObject().put("jobs",JSONArray().put(job))))
        if(!result.optBoolean("queued")) throw IOException("Publishing request was not accepted.")
        return result.optString("message","Job submitted to publisher.")
    }
    suspend fun runChecker():String =
        JSONObject(request("/api/admin/availability",JSONObject())).optString("message","Checker requested.")
    suspend fun resolveChecker(jobId:Int,action:String):String =
        JSONObject(request("/api/admin/review",JSONObject().put("jobId",jobId).put("action",action)))
            .optString("message","Review updated.")
    suspend fun registerAndroid(installation:String,token:String) {
        val j=JSONObject(request("/api/admin/android-devices",JSONObject()
            .put("action","register").put("installationId",installation).put("token",token)))
        if(!j.optBoolean("registered")) throw IOException("Notification registration not confirmed.")
    }
    suspend fun unregisterAndroid(installation:String) {
        request("/api/admin/android-devices",JSONObject().put("action","unregister").put("installationId",installation))
    }
    suspend fun testAndroidPush():Boolean =
        JSONObject(request("/api/admin/android-devices",JSONObject().put("action","test"))).optBoolean("ok")
}
