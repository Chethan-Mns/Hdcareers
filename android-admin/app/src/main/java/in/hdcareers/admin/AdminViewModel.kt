package `in`.hdcareers.admin

import android.app.Application
import android.content.Context
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.launch
import org.json.JSONObject
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue

class AdminViewModel(application:Application):AndroidViewModel(application) {
    private val api=AdminApi()
    private val vault=CredentialVault(application)
    var loggedIn by androidx.compose.runtime.mutableStateOf(false)
    var loading by androidx.compose.runtime.mutableStateOf(false)
    var busy by androidx.compose.runtime.mutableStateOf(false)
    var message by androidx.compose.runtime.mutableStateOf("")
    var tab by androidx.compose.runtime.mutableIntStateOf(0)
    var batch by androidx.compose.runtime.mutableStateOf(DailyBatch("","waiting",emptyList(),emptyList()))
    var jobs by androidx.compose.runtime.mutableStateOf<List<Job>>(emptyList())
    var companyLogos by androidx.compose.runtime.mutableStateOf<Map<String,CompanyLogoSource>>(emptyMap())
    var traffic by androidx.compose.runtime.mutableStateOf(Traffic())
    var days by androidx.compose.runtime.mutableIntStateOf(7)
    var checker by androidx.compose.runtime.mutableStateOf(JSONObject())
    var automation by androidx.compose.runtime.mutableStateOf(JSONObject())
    var fcmStatus by androidx.compose.runtime.mutableStateOf("Not configured")
    var manualDraft by androidx.compose.runtime.mutableStateOf<JSONObject?>(null)
    var manualUrl by androidx.compose.runtime.mutableStateOf("")
    var savedUsername=""
    private var savedPassword=""
    val hasBiometric get()=vault.exists

    private fun run(action:suspend ()->Unit) {
        viewModelScope.launch {
            busy=true
            try { action() } catch(e:Exception) { message=e.localizedMessage ?: "Operation failed." }
            finally { busy=false }
        }
    }
    fun login(user:String,password:String) = run {
        require(user.isNotBlank()&&password.isNotBlank()) { "Enter your admin username and password." }
        api.login(user.trim(),password)
        savedUsername=user.trim()
        savedPassword=password
        loggedIn=true
        refresh()
    }
    fun biometricSignIn() {
        try {
            val pair=vault.read()
            login(pair.first,pair.second)
        } catch(e:Exception) {
            message="Biometric access failed: "+(e.localizedMessage?:"Please sign in normally.")
        }
    }
    fun enableBiometric() {
        try {
            check(loggedIn && savedUsername.isNotBlank() && savedPassword.isNotBlank()) {
                "Sign in with your password before enabling biometrics."
            }
            vault.save(savedUsername,savedPassword)
            message="Fingerprint/device unlock enabled for your next login."
        } catch(e:Exception) { message=e.localizedMessage ?: "Biometric setup failed." }
    }
    fun logout()=run {
        api.logout()
        vault.clear()
        loggedIn=false
        savedUsername=""
        savedPassword=""
        jobs=emptyList()
        batch=DailyBatch("","waiting",emptyList(),emptyList())
    }
    private fun setReminderState() {
        val prefs=getApplication<Application>().getSharedPreferences("hd_review",Context.MODE_PRIVATE)
        prefs.edit().putBoolean("pending",batch.id.isNotBlank() && batch.status !in listOf("submitted","published") &&
                batch.priority.any { it.decision != "live" }).apply()
    }
    suspend fun refresh() {
        loading=true
        val errors= mutableListOf<String>()
        try { batch=api.batch();setReminderState() } catch(e:Exception){errors+="Review: "+e.message}
        try { jobs=api.jobs() } catch(e:Exception){errors+="Jobs: "+e.message}
        try { companyLogos=api.logoSources() } catch(_:Exception) { /* Show initials when the catalog is unavailable. */ }
        try { traffic=api.traffic(days) } catch(e:Exception){errors+="Analytics: "+e.message}
        try { checker=api.checker() } catch(e:Exception){errors+="Checker: "+e.message}
        try { automation=api.automation() } catch(e:Exception){errors+="Automation: "+e.message}
        loading=false
        if(errors.isNotEmpty()) message=errors.take(2).joinToString("\n")
    }
    fun refreshClicked()=run { refresh() }
    fun changeDays(value:Int)=run { days=value;traffic=api.traffic(value) }
    fun decide(id:String,decision:String)=run {
        batch=api.updateReview(batch.id,id,decision);setReminderState()
    }
    fun swap(priorityId:String,backupId:String)=run {
        batch=api.swap(batch.id,priorityId,backupId);setReminderState()
    }
    fun publishBatch()=run {
        check(batch.ready) { "Review 8 IT, 1 Non-IT and 1 training job as Live, with complete descriptions." }
        val snapshot=batch
        val confirmation=api.submit(snapshot)
        try {
            batch=api.markSubmitted(snapshot.id)
            setReminderState()
            message=confirmation+" Verify website deployment and Telegram delivery separately."
        } catch(e:Exception) {
            message="Publishing request accepted, but batch status could not be saved. Check GitHub before retrying: "+e.message
        }
    }
    fun checkerRun()=run { message=api.runChecker();checker=api.checker() }
    fun checkerResolve(id:Int,action:String)=run { message=api.resolveChecker(id,action);checker=api.checker() }
    fun extract(url:String)=run {
        require(url.startsWith("https://")) { "Enter a direct HTTPS job URL." }
        manualDraft=api.extractJob(url)
        message="Draft extracted. Review all details before publishing."
    }
    fun publishManual()=run {
        val draft=manualDraft?:error("Generate a job draft first.")
        check(draft.optString("company").isNotBlank() && draft.optString("role").isNotBlank()) {
            "The generated job is missing required information."
        }
        message=api.publishOne(draft)+" Confirm the website and Telegram delivery."
        manualDraft=null
    }
    fun connectPush() {
        fcmToken(getApplication(),onToken={token->
            getApplication<Application>().getSharedPreferences("hd_push",Context.MODE_PRIVATE)
                .edit().putString("token",token).apply()
            run {
                if(loggedIn) {
                    api.registerAndroid(installationId(getApplication()),token)
                    fcmStatus="Registered for live job alerts"
                }
            }
        },onError={fcmStatus=it})
    }
    fun testPush()=run {
        message=if(api.testAndroidPush()) "FCM accepted the test request. Check your Pixel notifications."
        else "Test push was not accepted. Check Firebase and server configuration."
    }
    fun toggleReminder(on:Boolean) {
        getApplication<Application>().getSharedPreferences("hd_review",Context.MODE_PRIVATE)
            .edit().putBoolean("reminder_enabled",on).apply()
        message=if(on)"Daily pending-review reminder enabled." else "Daily pending-review reminder disabled."
    }
}
