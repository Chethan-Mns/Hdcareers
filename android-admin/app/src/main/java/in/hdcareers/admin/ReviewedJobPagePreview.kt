package `in`.hdcareers.admin

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AssignmentTurnedIn
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.FileUpload
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.OpenInNew
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material.icons.filled.TipsAndUpdates
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch
import org.json.JSONObject

/**
 * Authenticated, strictly read-only representation of a reviewed Live candidate.
 *
 * This is intentionally a native Compose preview, not a public website URL or a
 * WebView rendering untrusted career-site HTML. It NEVER dispatches publishing
 * requests or uploads resumes. The production site still uses generate.py.
 */
@Composable
internal fun ReviewedJobPagePreview(
    candidate:Candidate,
    logos:Map<String,CompanyLogoSource>,
    onBack:()->Unit
) {
    if(!candidate.approved || candidate.job==null) {
        ProCard(Modifier.fillMaxWidth()) {
            Text("This job is no longer eligible for preview.",color=Brand.red)
            TextButton(onClick=onBack) { Text("Return to review") }
        }
        return
    }
    val job=candidate.job
    val role=job.optString("role").ifBlank { candidate.role }
    val source=job.optString("sourceName").ifBlank { "Official employer careers page" }
    val location=job.optString("loc").ifBlank { candidate.location }
    val experience=job.optString("expYears").ifBlank { "Not specified" }
    val qualification=job.optString("batch").ifBlank { "Not specified" }
    val salary=job.optString("salary").ifBlank { "Not disclosed" }
    val workMode=job.optString("workMode").ifBlank { "Not specified" }
    val skills=job.arrayStrings("skills")
    val tasks=job.arrayStrings("resp")
    val ctx=LocalContext.current
    val state=rememberLazyListState()
    val scope=rememberCoroutineScope()
    LazyColumn(
        state=state,modifier=Modifier.fillMaxSize(),
        contentPadding=PaddingValues(start=16.dp,end=16.dp,top=16.dp,bottom=30.dp),
        verticalArrangement=Arrangement.spacedBy(14.dp)
    ) {
        item {
            Surface(shape=RoundedCornerShape(24.dp),color=Brand.navy) {
                Column(
                    Modifier.fillMaxWidth()
                        .background(Brush.linearGradient(listOf(Brand.navy,Brand.darkBlue,Brand.blue)))
                        .padding(19.dp),
                    verticalArrangement=Arrangement.spacedBy(13.dp)
                ) {
                    Row(verticalAlignment=Alignment.CenterVertically,
                        horizontalArrangement=Arrangement.spacedBy(10.dp)) {
                        CompanyMark(candidate.company,logos,job,54)
                        Column(Modifier.weight(1f)) {
                            Text(candidate.company,color=Color.White,fontSize=19.sp,
                                fontWeight=FontWeight.Black)
                            Text("HD Careers · Candidate job page",color=Color.White.copy(alpha=.78f),
                                fontSize=11.sp)
                        }
                        Surface(color=Color(0xFFFFE3A6),shape=RoundedCornerShape(9.dp)) {
                            Text("PREVIEW",Modifier.padding(horizontal=9.dp,vertical=6.dp),
                                color=Brand.navy,fontSize=10.sp,fontWeight=FontWeight.Black)
                        }
                    }
                    Text(role,fontSize=23.sp,fontWeight=FontWeight.Black,
                        color=Color.White,lineHeight=28.sp)
                    Text(location+"  ·  "+experience,color=Color.White.copy(alpha=.86f),
                        fontSize=13.sp,lineHeight=18.sp)
                    Row(horizontalArrangement=Arrangement.spacedBy(7.dp)) {
                        ProPill("Verified Live",Brand.green)
                        ProPill(candidate.category.uppercase(),Brand.blue)
                    }
                    Text("Reviewed "+candidate.reviewedAt.take(10),
                        color=Color.White.copy(alpha=.72f),fontSize=11.sp)
                }
            }
        }
        item {
            ProCard {
                Row(verticalAlignment=Alignment.CenterVertically,
                    horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                    Icon(Icons.Default.Lock,null,tint=Brand.green)
                    Column {
                        Text("Private admin preview · Not published",
                            fontWeight=FontWeight.Black,color=Brand.navy,fontSize=14.sp)
                        Text("Read-only review using the verified job record. No public preview URL is created.",
                            fontSize=11.sp,color=Brand.gray,lineHeight=16.sp)
                    }
                }
                Row(horizontalArrangement=Arrangement.spacedBy(9.dp)) {
                    Button(
                        onClick={
                            if(candidate.apply.startsWith("https://"))
                                ctx.startActivity(Intent(Intent.ACTION_VIEW,Uri.parse(candidate.apply)))
                        },
                        modifier=Modifier.weight(1f),enabled=candidate.apply.startsWith("https://"),
                        shape=RoundedCornerShape(12.dp),
                        contentPadding=PaddingValues(horizontal=9.dp,vertical=13.dp)
                    ) {
                        Icon(Icons.Default.OpenInNew,null,Modifier.size(16.dp))
                        Spacer(Modifier.width(4.dp))
                        Text("Official source",fontSize=12.sp,maxLines=1)
                    }
                    OutlinedButton(
                        onClick={scope.launch { state.animateScrollToItem(3) }},
                        modifier=Modifier.weight(1f),shape=RoundedCornerShape(12.dp),
                        contentPadding=PaddingValues(horizontal=8.dp,vertical=13.dp)
                    ) {
                        Icon(Icons.Default.Description,null,Modifier.size(15.dp))
                        Spacer(Modifier.width(4.dp))
                        Text("Resume checker",fontSize=12.sp,maxLines=1)
                    }
                }
            }
        }
        item {
            ProCard {
                SectionHead(Icons.Default.AssignmentTurnedIn,"Job overview",
                    "Highlights sourced from the approved candidate",Brand.blue)
                Text(job.optString("desc"),color=Brand.navy,fontSize=13.sp,lineHeight=20.sp)
                HorizontalDivider(color=Brand.outline)
                for((label,value) in listOf(
                    "Experience" to experience,
                    "Qualification / Batch" to qualification,
                    "Work mode" to workMode,
                    "Salary / Stipend" to salary,
                    "Job location" to location
                )) {
                    Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween,
                        verticalAlignment=Alignment.Top) {
                        Text(label,fontSize=12.sp,color=Brand.gray,modifier=Modifier.weight(.48f))
                        Text(value,fontSize=12.sp,fontWeight=FontWeight.Bold,color=Brand.navy,
                            modifier=Modifier.weight(.52f))
                    }
                }
            }
        }
        item {
            ProCard {
                SectionHead(Icons.Default.FileUpload,"Check your resume for this job",
                    "Prominent visitor-facing resume checker",Brand.violet)
                Surface(color=Brand.sky,shape=RoundedCornerShape(15.dp),
                    border=BorderStroke(1.dp,Brand.blue.copy(alpha=.16f))) {
                    Column(Modifier.fillMaxWidth().padding(17.dp),
                        horizontalAlignment=Alignment.CenterHorizontally,
                        verticalArrangement=Arrangement.spacedBy(7.dp)) {
                        Icon(Icons.Default.FileUpload,"Resume upload preview",tint=Brand.blue,
                            modifier=Modifier.size(31.dp))
                        Text("Upload PDF, DOCX or TXT",fontWeight=FontWeight.Black,color=Brand.navy)
                        Text("Match skills and published requirements · No account needed",
                            color=Brand.gray,fontSize=11.sp)
                        Text("Visitor upload is disabled in Admin Preview",
                            color=Brand.blue,fontSize=11.sp,fontWeight=FontWeight.Bold)
                    }
                }
                Text("The live page uses the existing browser-side resume matcher. It does not upload the resume to HD Careers; results are estimates, not employer ATS scores.",
                    fontSize=11.sp,color=Brand.gray,lineHeight=17.sp)
                if(skills.isNotEmpty()) Text("Skills the matcher will look for: "+skills.take(7).joinToString(", "),
                    color=Brand.navy,fontSize=12.sp,lineHeight=18.sp)
            }
        }
        item {
            ProCard {
                SectionHead(Icons.Default.Shield,"Eligibility & responsibilities",
                    "Display only details recorded from the official source",Brand.blue)
                Text(job.optString("elig"),color=Brand.navy,fontSize=13.sp,lineHeight=20.sp)
                if(tasks.isNotEmpty()){
                    HorizontalDivider(color=Brand.outline)
                    Text("Main responsibilities",fontSize=13.sp,fontWeight=FontWeight.Black,color=Brand.navy)
                    tasks.take(6).forEach {
                        Text("• "+it,color=Brand.navy,fontSize=12.sp,lineHeight=19.sp)
                    }
                }
                if(skills.isNotEmpty()){
                    HorizontalDivider(color=Brand.outline)
                    Text("Skills mentioned",fontSize=13.sp,fontWeight=FontWeight.Black,color=Brand.navy)
                    skills.take(12).forEach {
                        Text("• "+it,fontSize=12.sp,color=Brand.navy)
                    }
                }
            }
        }
        item {
            ProCard {
                SectionHead(Icons.Default.TipsAndUpdates,"Application guidance",
                    "No fabricated salary, stages or eligibility",Brand.green)
                Text("1. Compare the published requirements with your real qualifications.",
                    fontSize=12.sp,color=Brand.navy)
                Text("2. Check your resume and update only skills you genuinely have.",
                    fontSize=12.sp,color=Brand.navy)
                Text("3. Apply using the exact official link; verify its current status.",
                    fontSize=12.sp,color=Brand.navy)
                HorizontalDivider(color=Brand.outline)
                Text("Source: "+source,fontSize=12.sp,color=Brand.gray)
                Text("Recorded verification: "+job.optString("verifiedDate").ifBlank { candidate.reviewedAt.take(10) },
                    fontSize=12.sp,color=Brand.gray)
                Text("Design review only. The HTML generated by generate.py is the final public implementation.",
                    fontSize=11.sp,color=Brand.amber)
            }
        }
        item {
            OutlinedButton(onClick=onBack,modifier=Modifier.fillMaxWidth(),
                shape=RoundedCornerShape(12.dp)) {
                Text("Return to approved-job review")
            }
        }
    }
}

private fun JSONObject.arrayStrings(name:String):List<String> {
    val src=optJSONArray(name) ?: return emptyList()
    return (0 until src.length()).mapNotNull{ src.optString(it).trim().takeIf(String::isNotBlank) }
}
