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
    var adminRole by androidx.compose.runtime.mutableStateOf("owner")
    var loading by androidx.compose.runtime.mutableStateOf(false)
    var busy by androidx.compose.runtime.mutableStateOf(false)
    var message by androidx.compose.runtime.mutableStateOf("")
    var tab by androidx.compose.runtime.mutableIntStateOf(0)
    var batch by androidx.compose.runtime.mutableStateOf(DailyBatch("","waiting",emptyList(),emptyList()))
    var selectedIds by androidx.compose.runtime.mutableStateOf<Set<String>>(emptySet())
    var publishedReviewIds by androidx.compose.runtime.mutableStateOf<Set<String>>(emptySet())
    var publishingProgress by androidx.compose.runtime.mutableStateOf(JSONObject())
    val selectedBlockers get()=batch.selectedBlockers(selectedIds,publishedReviewIds)
    val canPublish get()=selectedBlockers.isEmpty()
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
        adminRole=api.login(user.trim(),password)
        savedUsername=user.trim()
        savedPassword=password
        loggedIn=true
        refresh()
        ensurePushConnected()
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
        if(loggedIn)runCatching { api.unregisterAndroid(installationId(getApplication())) }
        api.logout()
        vault.clear()
        loggedIn=false
        adminRole="owner"
        savedUsername=""
        savedPassword=""
        jobs=emptyList()
        traffic=Traffic()
        batch=DailyBatch("","waiting",emptyList(),emptyList())
        selectedIds=emptySet()
        publishedReviewIds=emptySet()
        publishingProgress=JSONObject()
    }
    private fun setReminderState() {
        val prefs=getApplication<Application>().getSharedPreferences("hd_review",Context.MODE_PRIVATE)
        prefs.edit().putBoolean("pending",batch.id.isNotBlank() && batch.status !in listOf("submitted","published") &&
                batch.priority.any { it.decision != "live" }).apply()
    }
    suspend fun refresh() {
        loading=true
        val errors= mutableListOf<String>()
        try {
            val latest=api.batch()
            if(latest.id!=batch.id) {
                selectedIds=emptySet()
                publishedReviewIds=emptySet()
                publishingProgress=JSONObject()
            }
            batch=latest
            selectedIds=selectedIds.filterTo(mutableSetOf()) { id ->
                latest.all.any { it.id==id && it.selectable }
            }
            setReminderState()
        } catch(e:Exception){errors+="Review: "+e.message}
        try { jobs=api.jobs() } catch(e:Exception){errors+="Jobs: "+e.message}
        try { companyLogos=api.logoSources() } catch(_:Exception) { /* Show initials when the catalog is unavailable. */ }
        try { traffic=api.traffic(days) } catch(e:Exception){errors+="Analytics: "+e.message}
        try { checker=api.checker() } catch(e:Exception){errors+="Checker: "+e.message}
        try { automation=api.automation() } catch(e:Exception){errors+="Automation: "+e.message}
        runCatching { loadPublishingProgress() }
        loading=false
        if(errors.isNotEmpty()) message=errors.take(2).joinToString("\n")
    }
    fun refreshClicked()=run { refresh() }
    fun changeDays(value:Int)=run {
        days=value;traffic=api.traffic(value)
    }
    private suspend fun loadPublishingProgress() {
        val data=api.publishProgress()
        if(data.optString("batchId")==batch.id) {
            publishingProgress=data
            val arr=data.optJSONArray("publishedCandidateIds")
            publishedReviewIds=(0 until (arr?.length() ?: 0)).map { arr!!.optString(it) }.toSet()
            selectedIds=selectedIds-publishedReviewIds
        }
    }
    fun refreshPublishingStatus()=run { loadPublishingProgress() }
    fun refreshPublishingStatusQuietly() {
        viewModelScope.launch { runCatching { loadPublishingProgress() } }
    }
    fun toggleSelected(id:String,checked:Boolean) {
        val c=batch.all.firstOrNull { it.id==id } ?: return
        if(!checked){selectedIds=selectedIds-id;return}
        if(!c.selectable){message="Verify the official job URL as Live before moving it to Publish Ready.";return}
        if(id in publishedReviewIds){message="That job is already published.";return}
        if(selectedIds.size>=10){message="Select a maximum of 10 jobs.";return}
        if(batch.all.any { it.id in selectedIds&&employerKey(it.company)==employerKey(c.company) }){
            message="Select only one job per employer, including aliases.";return
        }
        selectedIds=selectedIds+id
        if(!c.approved) run {
            try {
                batch=api.enrich(batch.id,id)
                setReminderState()
                message="Recovered available job details from the official listing. Check Publish Ready."
            } catch(e:Exception) {
                message="Moved to Publish Ready, but source details remain incomplete: "+
                    (e.localizedMessage ?: "The official page could not be verified.")
            }
        }
    }
    // Owner explicitly checked the exact official listing, then verifies and selects in one action.
    fun verifyAndAdd(id:String)=run {
        val original=batch.all.firstOrNull{it.id==id} ?: error("Candidate no longer exists.")
        check(original.apply.startsWith("https://")) { "Open the exact official link before verifying." }
        check(batch.status !in listOf("submitted","published")) { "Refresh: this batch was submitted." }
        check(selectedIds.size<10) { "The daily maximum is ten jobs." }
        check(batch.all.none { it.id in selectedIds && employerKey(it.company)==employerKey(original.company) }) {
            "Only one job per employer is permitted."
        }
        if(original.decision!="live")batch=api.updateReview(batch.id,id,"live")
        var candidate=batch.all.firstOrNull{it.id==id} ?: error("Updated candidate missing.")
        if(!candidate.complete) {
            batch=api.enrich(batch.id,id)
            candidate=batch.all.firstOrNull{it.id==id} ?: error("Enriched candidate missing.")
        }
        setReminderState()
        if(candidate.approved && id !in publishedReviewIds){
            selectedIds=selectedIds+id
            message=candidate.company+" verified and added to Publish Ready."
        } else message=candidate.company+" held: "+candidate.missingDetails.joinToString(", ")+
            ". No publishing request was sent."
    }
    fun refreshExpiry()=run { checker=api.checker() }
    fun refreshOperationsQuietly() {
        if(!loggedIn) return
        viewModelScope.launch {
            runCatching { checker=api.checker() }
            runCatching { automation=api.automation() }
        }
    }
    fun ensurePushConnected(){
        if(!loggedIn||!firebaseReady(getApplication()))return
        val prefs=getApplication<Application>().getSharedPreferences("hd_push",Context.MODE_PRIVATE)
        if(prefs.getBoolean("consented",false)||!prefs.getString("token",null).isNullOrBlank())connectPush()
    }
    fun decide(id:String,decision:String)=run {
        batch=api.updateReview(batch.id,id,decision);setReminderState()
        if(decision!="live")selectedIds=selectedIds-id
    }
    fun swap(priorityId:String,backupId:String)=run {
        batch=api.swap(batch.id,priorityId,backupId);setReminderState()
    }
    fun publishBatch()=run {
        check(canPublish) { "Publishing blocked: " + selectedBlockers.take(4).joinToString(" | ") }
        val snapshot=batch
        val chosen=selectedIds.toSet()
        val (confirmation,requestId)=api.submit(snapshot,chosen)
        try {
            batch=api.markSubmitted(snapshot.id,chosen,requestId)
            setReminderState()
            message=confirmation+" Website publication will be checked before hourly Telegram delivery."
            runCatching { loadPublishingProgress() }
        } catch(e:Exception) {
            message="GitHub accepted the request but review status could not be saved. Do not retry without checking the tracker: "+e.message
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
        if(!loggedIn){fcmStatus="Sign in before enabling notifications.";return}
        getApplication<Application>().getSharedPreferences("hd_push",Context.MODE_PRIVATE)
            .edit().putBoolean("consented",true).apply()
        fcmStatus="Connecting to Firebase…"
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
