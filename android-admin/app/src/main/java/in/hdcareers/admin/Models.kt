package in.hdcareers.admin

import org.json.JSONArray
import org.json.JSONObject

data class Job(
    val id: String, val company: String, val role: String, val location: String,
    val cat: String, val status: String, val apply: String, val exp: String, val page: String, val raw: JSONObject
)
data class Candidate(
    val id: String, val company: String, val role: String, val location: String,
    val category: String, val apply: String, val experience: String, val decision: String,
    val job: JSONObject?
) {
    val group: String get() = when(category.lowercase()) {
        "nonit" -> "nonit"; "internship", "apprenticeship" -> "training"; else -> "it"
    }
    val complete: Boolean get() = job?.let {
        listOf("company","role","loc","elig","desc","apply").all { key -> it.optString(key).isNotBlank() } &&
            (it.optJSONArray("resp")?.length() ?: 0) > 0
    } ?: false
}
data class DailyBatch(val id: String, val status: String, val priority: List<Candidate>, val backup: List<Candidate>) {
    val reviewed: Int get() = (priority + backup).count { it.decision in listOf("live","expired","unsure") }
    val ready: Boolean get() = id.isNotBlank() && priority.size == 10 &&
        status !in listOf("submitted","published") &&
        priority.all { it.decision == "live" && it.complete } &&
        priority.map { it.company.trim().lowercase() }.distinct().size == 10 &&
        priority.count { it.group == "it" } == 8 &&
        priority.count { it.group == "nonit" } == 1 &&
        priority.count { it.group == "training" } == 1
}
data class Traffic(val users: Int=0, val views: Int=0, val live: Int=0,
                   val applies: Int=0, val resumes: Int=0,
                   val countries: List<Pair<String,Int>> = emptyList(),
                   val pages: List<Pair<String,Int>> = emptyList(),
                   val devices: List<Pair<String,Int>> = emptyList())

fun JSONObject.array(key: String): List<JSONObject> {
    val source = optJSONArray(key) ?: return emptyList()
    return (0 until source.length()).mapNotNull { source.optJSONObject(it) }
}
fun parseCandidate(j: JSONObject): Candidate {
    val detail=j.optJSONObject("job")
    fun string(field:String)=j.optString(field).ifBlank { detail?.optString(field).orEmpty() }
    return Candidate(j.optString("id"),string("company"),string("role"),string("loc"),
        string("cat").ifBlank { "it" }, string("apply"),string("expYears"),
        j.optString("reviewedStatus"),detail)
}
fun parseBatch(json: JSONObject): DailyBatch = DailyBatch(
    json.optString("batchId"),json.optString("status"),
    json.array("priority").map(::parseCandidate),json.array("backup").map(::parseCandidate)
)
fun parseJobs(raw: JSONArray): List<Job> = (0 until raw.length()).mapNotNull { i ->
    raw.optJSONObject(i)?.let {
        Job(it.optString("id",i.toString()),it.optString("company"),it.optString("role"),
            it.optString("loc"),it.optString("cat"),it.optString("status","active"),
            it.optString("apply"),it.optString("expYears"),it.optString("page"),it)
    }
}
fun parseTraffic(j:JSONObject): Traffic {
    fun counts(key:String,value:String)=j.array(key).take(8).map { it.optString(value,"Unknown") to
        it.optInt(if(key=="pages")"pageviews" else "visitors") }
    return Traffic(j.optJSONObject("totals")?.optInt("visitors")?:0,
        j.optJSONObject("totals")?.optInt("pageviews")?:0,j.optInt("realtimeUsers"),
        j.optJSONObject("conversions")?.optInt("applyClicks")?:0,
        j.optJSONObject("conversions")?.optInt("resumeChecks")?:0,
        counts("countries","country"),counts("pages","requestPath"),counts("devices","deviceType"))
}
