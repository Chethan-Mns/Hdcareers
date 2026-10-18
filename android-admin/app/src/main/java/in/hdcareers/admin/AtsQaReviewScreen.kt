package `in`.hdcareers.admin

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.Toast
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.SubcomposeAsyncImage
import org.json.JSONArray
import org.json.JSONObject
import java.net.URLEncoder

private val qaBlue=Color(0xFF1566BD)
private val qaInk=Color(0xFF153052)
private val qaMuted=Color(0xFF6B7F97)

private data class QaRole(val id:String,val company:String,val provider:String,val role:String,
    val location:String,val url:String,val req:String,val domain:String,val notes:String)

private fun sample(context:Context):List<QaRole>{
 val data=JSONObject(context.assets.open("ats-platform-seven.json").bufferedReader().use{it.readText()})
 val rows=data.getJSONArray("jobs")
 return (0 until rows.length()).map{i->
  val j=rows.getJSONObject(i)
  QaRole(j.getString("id"),j.getString("company"),j.getString("provider"),
    j.getString("role"),j.getString("location"),j.getString("url"),
    j.getString("reqId"),j.getString("brandDomain"),j.optString("notes"))
 }
}

@Composable
fun AtsPlatformQaScreen(onBack:(()->Unit)?=null){
 val ctx=androidx.compose.ui.platform.LocalContext.current
 val jobs=remember{sample(ctx)}
 val prefs=remember{ctx.getSharedPreferences("ats_platform_qa",Context.MODE_PRIVATE)}
 val verdicts=remember{mutableStateMapOf<String,String>().apply{
  jobs.forEach{j->this[j.id]=prefs.getString(j.id,"unreviewed")?:"unreviewed"}
 }}
 var selected by remember{mutableStateOf(emptySet<String>())}
 var simulated by remember{mutableStateOf(false)}
 var confirmation by remember{mutableStateOf(false)}
 fun decide(id:String,value:String){
  verdicts[id]=value
  prefs.edit().putString(id,value).apply()
  if(value!="live")selected=selected-id
  simulated=false
 }
 fun copy(){
  val items=JSONArray()
  jobs.forEach{j->
   items.put(JSONObject().put("provider",j.provider).put("company",j.company)
     .put("role",j.role).put("officialUrl",j.url)
     .put("manualVerdict",verdicts[j.id]?:"unreviewed")
     .put("selectedForQaPublish",j.id in selected))
  }
  val report=JSONObject().put("batchId","ats-seven-sources-2026-10-18")
    .put("type","QA_OFFLINE_NO_PUBLICATION")
    .put("jobs",items).toString(2)
  val cb=ctx.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
  cb.setPrimaryClip(ClipData.newPlainText("HD Careers QA decisions",report))
  Toast.makeText(ctx,"Decisions copied. Paste into ChatGPT to compare accuracy.",Toast.LENGTH_LONG).show()
 }
 MaterialTheme {
  LazyColumn(modifier=Modifier.fillMaxSize().background(Color(0xFFF4F8FC)),
   contentPadding=PaddingValues(16.dp),verticalArrangement=Arrangement.spacedBy(13.dp)){
   item {
    if(onBack!=null) TextButton(onClick=onBack) { Text("Back to HD Careers Admin",color=qaBlue) }
    Surface(color=qaInk,shape=RoundedCornerShape(22.dp)){
     Column(Modifier.padding(19.dp),verticalArrangement=Arrangement.spacedBy(6.dp)){
      Text("HD CAREERS · ISOLATED QA",color=Color(0xFF9BD1FF),fontSize=11.sp,fontWeight=FontWeight.Black)
      Text("${jobs.size} ATS platforms",color=Color.White,fontSize=24.sp,fontWeight=FontWeight.Black)
      Text("Test real official links, employer logos and review decisions. Publishing is SIMULATED — no website or Telegram changes.",
       color=Color.White,fontSize=12.sp)
      Text("Live ${jobs.count{verdicts[it.id]=="live"}}   •   Expired ${jobs.count{verdicts[it.id]=="expired"}}   •   Unsure ${jobs.count{verdicts[it.id]=="unsure"}}",
       color=Color(0xFFB3DEFF),fontSize=12.sp,fontWeight=FontWeight.Bold)
     }
    }
   }
   items(jobs,key={it.id}){job->
    Surface(shape=RoundedCornerShape(18.dp),color=Color.White,
     border=BorderStroke(1.dp,Color(0xFFDCE6F2)),shadowElevation=2.dp){
     Column(Modifier.padding(14.dp),verticalArrangement=Arrangement.spacedBy(8.dp)){
      Row(verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(10.dp)){
       val uri="https://www.google.com/s2/favicons?domain_url="+
        URLEncoder.encode("https://"+job.domain,"UTF-8")+"&sz=256"
       Surface(shape=RoundedCornerShape(10.dp),color=Color(0xFFF0F5FF)){
        SubcomposeAsyncImage(model=uri,contentDescription=job.company+" company favicon",
         contentScale=ContentScale.Fit,modifier=Modifier.size(52.dp).padding(7.dp),
         loading={Box(Modifier.fillMaxSize(),contentAlignment=Alignment.Center){
          Text(job.company.take(2).uppercase(),fontWeight=FontWeight.Black,color=qaBlue)}},
         error={Box(Modifier.fillMaxSize(),contentAlignment=Alignment.Center){
          Text(job.company.take(2).uppercase(),fontWeight=FontWeight.Black,color=qaBlue)}}
        )
       }
       Column(Modifier.weight(1f)){
        Text(job.company,fontSize=16.sp,fontWeight=FontWeight.Black,color=qaInk)
        Text(job.provider+" · "+job.location,fontSize=11.sp,color=qaMuted)
       }
      }
      Text(job.role,fontSize=14.sp,fontWeight=FontWeight.Bold,color=qaInk)
      Text("Requisition: "+job.req,fontSize=11.sp,color=qaMuted)
      Text(job.notes,fontSize=11.sp,color=qaMuted)
      Text("Review: "+(verdicts[job.id]?:"unreviewed").uppercase(),
       fontSize=11.sp,fontWeight=FontWeight.Bold,color=qaBlue)
      OutlinedButton(onClick={
       ctx.startActivity(Intent(Intent.ACTION_VIEW,Uri.parse(job.url)))
      },modifier=Modifier.fillMaxWidth()){Text("Open exact official job ↗")}
      Row(horizontalArrangement=Arrangement.spacedBy(5.dp)){
       listOf("live" to "Live","expired" to "Expired","unsure" to "Unsure").forEach{(state,title)->
        if(verdicts[job.id]==state)Button(onClick={decide(job.id,state)},modifier=Modifier.weight(1f),
         contentPadding=PaddingValues(5.dp)){Text("✓"+title,fontSize=11.sp)}
        else OutlinedButton(onClick={decide(job.id,state)},modifier=Modifier.weight(1f),
         contentPadding=PaddingValues(5.dp)){Text(title,fontSize=11.sp)}
       }
      }
      if(verdicts[job.id]=="live"){
       Row(verticalAlignment=Alignment.CenterVertically){
        Checkbox(checked=job.id in selected,onCheckedChange={yes->
         selected=if(yes)selected+job.id else selected-job.id
         simulated=false
        })
        Text("Select for QA Publish rehearsal",fontSize=12.sp,color=qaInk)
       }
      }
     }
    }
   }
   item{
    Surface(shape=RoundedCornerShape(18.dp),color=Color.White,
     border=BorderStroke(1.dp,Color(0xFFDCE6F2))){
     Column(Modifier.padding(16.dp),verticalArrangement=Arrangement.spacedBy(10.dp)){
      Text("Safe publishing rehearsal",fontSize=18.sp,fontWeight=FontWeight.Black,color=qaInk)
      Text("${selected.size} manually confirmed Live job(s) selected. No backend request can be sent from this QA screen.",
       fontSize=12.sp,color=qaMuted)
      Button(onClick={confirmation=true},enabled=selected.isNotEmpty(),
       modifier=Modifier.fillMaxWidth()){
       Text("Simulate Publish · ${selected.size} job(s)")
      }
      if(simulated)Text("✓ Local QA simulation completed.\nWebsite: NOT DEPLOYED\nTelegram: NOT SENT",
       color=Color(0xFF09794E),fontSize=12.sp,fontWeight=FontWeight.Bold)
      OutlinedButton(onClick={copy()},modifier=Modifier.fillMaxWidth()){
       Text("Copy decisions for accuracy comparison")
      }
      Text("Paste the copied results into this chat. The production HD Careers Admin remains untouched.",
       fontSize=11.sp,color=qaMuted)
     }
    }
   }
  }
  if(confirmation)AlertDialog(onDismissRequest={confirmation=false},
   title={Text("QA simulation only")},
   text={Text("Verify ${selected.size} selected jobs in the dry-run. Nothing posts to the live website or Telegram.")},
   confirmButton={TextButton(onClick={confirmation=false;simulated=true}){Text("Run simulation")}},
   dismissButton={TextButton(onClick={confirmation=false}){Text("Cancel")}})
 }
}
