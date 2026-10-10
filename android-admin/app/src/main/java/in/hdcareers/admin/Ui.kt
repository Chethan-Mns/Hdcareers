package in.hdcareers.admin

import android.content.Intent
import android.net.Uri
import androidx.compose.animation.animateContentSize
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import org.json.JSONObject

private val Navy=Color(0xFF102D55)
private val Blue=Color(0xFF1169D7)
private val Teal=Color(0xFF008F82)
private val Pale=Color(0xFFF4F7FC)
private val Gray=Color(0xFF637890)
private val Red=Color(0xFFBE3448)
private val Amber=Color(0xFFB57A19)
private val themeColors=lightColorScheme(primary=Blue,secondary=Teal,background=Pale,surface=Color.White,onSurface=Navy)
private val rounded=RoundedCornerShape(18.dp)

@Composable
fun AdminRoot(vm:AdminViewModel,onBiometricSignIn:()->Unit,onEnableBiometric:()->Unit,onRequestNotificationPermission:()->Unit) {
    MaterialTheme(colorScheme=themeColors,typography=Typography()) {
        Surface(color=Pale,modifier=Modifier.fillMaxSize()) {
            if(!vm.loggedIn) LoginPage(vm,onBiometricSignIn)
            else Scaffold(
                bottomBar={
                    NavigationBar(containerColor=Color.White) {
                        val labels=listOf("Home","Review","Jobs","More")
                        val icons=listOf(Icons.Default.Home,Icons.Default.FactCheck,Icons.Default.Work,Icons.Default.MoreHoriz)
                        labels.forEachIndexed { index,label ->
                            NavigationBarItem(selected=vm.tab==index,onClick={vm.tab=index},
                                icon={ Icon(icons[index],null) },label={Text(label,maxLines=1)})
                        }
                    }
                },
                snackbarHost={},
                containerColor=Pale
            ) { padding ->
                Column(Modifier.fillMaxSize().padding(padding)) {
                    Row(Modifier.fillMaxWidth().background(Color.White).padding(horizontal=18.dp, vertical=14.dp),
                        verticalAlignment=Alignment.CenterVertically) {
                        Text("HD",fontSize=19.sp,fontWeight=FontWeight.Black,color=Blue)
                        Spacer(Modifier.width(10.dp))
                        Text(listOf("Overview","Daily Review","Job Management","More")[vm.tab],
                            fontWeight=FontWeight.ExtraBold,fontSize=20.sp,modifier=Modifier.weight(1f))
                        IconButton(onClick={vm::refreshClicked}) {Icon(Icons.Default.Refresh,"Refresh")}
                    }
                    if(vm.loading) LinearProgressIndicator(Modifier.fillMaxWidth())
                    when(vm.tab) {
                        0 -> HomePage(vm)
                        1 -> ReviewPage(vm)
                        2 -> JobsPage(vm)
                        else -> MorePage(vm,onEnableBiometric,onRequestNotificationPermission)
                    }
                }
            }
        }
        if(vm.message.isNotBlank()) AlertDialog(
            onDismissRequest={vm.message=""},title={Text("HD Careers Admin")},
            text={Text(vm.message)},confirmButton={TextButton(onClick={vm.message=""}){Text("OK")}})
    }
}
@Composable private fun LoginPage(vm:AdminViewModel,biometric:()->Unit) {
    var username by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(24.dp),
        verticalArrangement=Arrangement.Center) {
        Box(Modifier.size(64.dp).background(Navy,rounded),contentAlignment=Alignment.Center){
            Text("HD",color=Color.White,fontSize=24.sp,fontWeight=FontWeight.Black)}
        Spacer(Modifier.height(22.dp))
        Text("HD Careers Admin",fontSize=28.sp,fontWeight=FontWeight.Black)
        Text("Private publishing control center",color=Gray)
        Spacer(Modifier.height(28.dp))
        OutlinedTextField(username,{username=it},label={Text("Username")},singleLine=true,modifier=Modifier.fillMaxWidth())
        Spacer(Modifier.height(12.dp))
        OutlinedTextField(password,{password=it},label={Text("Password")},
            visualTransformation=androidx.compose.ui.text.input.PasswordVisualTransformation(),
            singleLine=true,modifier=Modifier.fillMaxWidth())
        Spacer(Modifier.height(18.dp))
        Button(onClick={vm.login(username,password)},enabled=!vm.busy,
            modifier=Modifier.fillMaxWidth().height(52.dp)){Text("Secure Sign In")}
        if(vm.hasBiometric) {
            TextButton(onClick=biometric,modifier=Modifier.fillMaxWidth()){
                Icon(Icons.Default.Fingerprint,null);Spacer(Modifier.width(8.dp));Text("Unlock with fingerprint")}
        }
        Spacer(Modifier.height(20.dp))
        Text("Your admin session and publishing credentials remain on the secure HD Careers server.",
            color=Gray,fontSize=12.sp)
    }
}
@Composable private fun CardSection(title:String,subtitle:String?=null,content:@Composable ColumnScope.()->Unit) {
    Card(Modifier.fillMaxWidth(),shape=rounded,colors=CardDefaults.cardColors(containerColor=Color.White)) {
        Column(Modifier.padding(16.dp),verticalArrangement=Arrangement.spacedBy(10.dp)){
            Text(title,fontWeight=FontWeight.Bold,fontSize=17.sp)
            if(subtitle!=null) Text(subtitle,fontSize=12.sp,color=Gray)
            content()
        }
    }
}
@Composable private fun Metric(label:String,value:String,modifier:Modifier=Modifier) {
    Card(modifier,shape=RoundedCornerShape(14.dp),colors=CardDefaults.cardColors(containerColor=Color.White)){
        Column(Modifier.padding(14.dp)){
            Text(value,fontSize=23.sp,fontWeight=FontWeight.Black,color=Navy)
            Text(label,color=Gray,fontSize=12.sp)
        }
    }
}
@Composable private fun TwoMetricRows(values:List<Pair<String,String>>) {
    Column(verticalArrangement=Arrangement.spacedBy(9.dp)){
        values.chunked(2).forEach { part ->
            Row(horizontalArrangement=Arrangement.spacedBy(9.dp)) {
                part.forEach { (label,value)->Metric(label,value,Modifier.weight(1f)) }
                if(part.size==1) Spacer(Modifier.weight(1f))
            }
        }
    }
}
@Composable private fun HomePage(vm:AdminViewModel) {
    val active=vm.jobs.count{it.status=="active"}
    val pending=vm.batch.priority.count{it.decision!="live"}
    LazyColumn(contentPadding=PaddingValues(16.dp),verticalArrangement=Arrangement.spacedBy(14.dp)){
        item { Text("Your daily operations",fontSize=24.sp,fontWeight=FontWeight.Black) }
        item {
            Card(onClick={vm.tab=1},shape=rounded,colors=CardDefaults.cardColors(containerColor=Navy)){
                Column(Modifier.padding(18.dp)){
                    Text("TODAY'S JOB REVIEW",color=Color.White.copy(alpha=.7f),fontSize=11.sp,letterSpacing=1.sp)
                    Text(if(vm.batch.id.isBlank())"Awaiting discovery" else "${vm.batch.priority.size + vm.batch.backup.size} jobs in your inbox",
                        color=Color.White,fontSize=22.sp,fontWeight=FontWeight.Bold)
                    Text(if(vm.batch.id.isBlank())"The discovery workflow hasn't saved a batch yet."
                    else "$pending priority jobs need confirmation.",color=Color.White.copy(alpha=.8f))
                }
            }
        }
        item { TwoMetricRows(listOf("Total jobs" to "${vm.jobs.size}","Active" to "$active",
            "Freshers" to "${vm.jobs.count{it.status=="active" && it.raw.optString("expType")=="fresher"}}",
            "Expired" to "${vm.jobs.count{it.status=="expired"}}")) }
        item { CardSection("Website analytics","Google Analytics snapshot") {
            TwoMetricRows(listOf("Visitors" to "${vm.traffic.users}","Page views" to "${vm.traffic.views}",
                "Live users" to "${vm.traffic.live}","Apply clicks" to "${vm.traffic.applies}"))
            OutlinedButton(onClick={vm.tab=3}){Text("Explore analytics →")}
        }}
        item { CardSection("Automation status") {
            Text(vm.automation.optString("lastUpdated", "Review latest run status in GitHub Actions."),
                color=Gray,fontSize=13.sp)
            OutlinedButton(onClick=vm::refreshClicked){Text("Refresh status")}
        }}
    }
}
@Composable private fun ReviewPage(vm:AdminViewModel) {
    var selected by remember { mutableIntStateOf(0) }
    var confirm by remember { mutableStateOf(false) }
    val visible=if(selected==0)vm.batch.priority else vm.batch.backup
    LazyColumn(contentPadding=PaddingValues(16.dp),verticalArrangement=Arrangement.spacedBy(12.dp)){
        item {
            CardSection("Daily Review Center","Ten priority jobs, ten category-matched backup options") {
                TwoMetricRows(listOf("Priority" to "${vm.batch.priority.size}",
                    "Backups" to "${vm.batch.backup.size}","Reviewed" to "${vm.batch.reviewed}",
                    "Verified Live" to "${(vm.batch.priority+vm.batch.backup).count{it.decision=="live"}}"))
                TabRow(selectedTabIndex=selected) {
                    listOf("Priority 10","Backup 10").forEachIndexed{index,name->
                        Tab(selected=selected==index,onClick={selected=index},text={Text(name)})
                    }
                }
            }
        }
        if(vm.batch.id.isBlank()) item { CardSection("Waiting for today's shortlist") {
            Text("No jobs have been inserted as placeholders. The discovery pipeline must publish a real 20-job review batch.")
        }}
        items(visible,key={it.id}) { job ->
            CandidateCard(job,selected==0,vm.batch.backup,vm.busy,
                onDecision={vm.decide(job.id,it)},onSwap={vm.swap(job.id,it)})
        }
        if(selected==0 && vm.batch.id.isNotBlank()) item {
            CardSection("Publish the verified Top 10") {
                Text("Requires 8 fresher IT, 1 non-IT and 1 training job from 10 distinct employers, all reviewed Live with complete descriptions.",
                    color=Gray,fontSize=12.sp)
                Button(onClick={confirm=true},modifier=Modifier.fillMaxWidth(),enabled=vm.batch.ready && !vm.busy){
                    Text("Approve and start publishing")
                }
                Text("Dispatch accepted ≠ website deployed or Telegram delivered. Verify delivery separately.",
                    fontSize=12.sp,color=Gray)
            }
        }
    }
    if(confirm) AlertDialog(onDismissRequest={confirm=false},title={Text("Publish reviewed jobs?")},
        text={Text("This submits the approved ten jobs to the existing GitHub publishing pipeline.")},
        confirmButton={TextButton(onClick={confirm=false;vm.publishBatch()}){Text("Publish")}},
        dismissButton={TextButton(onClick={confirm=false}){Text("Cancel")}})
}
@Composable private fun CandidateCard(c:Candidate,priority:Boolean,backups:List<Candidate>,busy:Boolean,
    onDecision:(String)->Unit,onSwap:(String)->Unit) {
    var expanded by remember { mutableStateOf(false) }
    val context=LocalContext.current
    val choices=backups.filter{it.group==c.group&&it.decision=="live" && it.company!=c.company}
    CardSection(c.company,c.role) {
        Text(listOf(c.location,c.experience).filter{it.isNotBlank()}.joinToString(" · "),color=Gray,fontSize=12.sp)
        Text(when(c.group){"nonit"->"Non-IT";"training"->"Internship / Apprenticeship";else->"Fresher IT"},
            fontSize=12.sp,color=Blue,fontWeight=FontWeight.SemiBold)
        if(c.apply.startsWith("https://")) TextButton(onClick={
            context.startActivity(Intent(Intent.ACTION_VIEW,Uri.parse(c.apply)))}) {
            Icon(Icons.Default.OpenInNew,null);Spacer(Modifier.width(6.dp));Text("Official application link")
        }
        Row(horizontalArrangement=Arrangement.spacedBy(5.dp)){
            listOf("live","expired","unsure").forEach{decision->
                val active=c.decision==decision
                val color=when(decision){"live"->Teal;"expired"->Red;else->Amber}
                OutlinedButton(onClick={onDecision(decision)},enabled=!busy,
                    colors=ButtonDefaults.outlinedButtonColors(containerColor=if(active)color.copy(alpha=.15f) else Color.Transparent),
                    contentPadding=PaddingValues(horizontal=11.dp,vertical=0.dp),modifier=Modifier.weight(1f)){
                    Text(decision.replaceFirstChar{it.uppercase()},fontSize=11.sp,color=color,maxLines=1)
                }
            }
        }
        if(priority) {
            Box {
                OutlinedButton(onClick={expanded=true},enabled=choices.isNotEmpty()&&!busy) {
                    Icon(Icons.Default.SwapHoriz,null);Spacer(Modifier.width(7.dp));Text("Replace from Backup")
                }
                DropdownMenu(expanded=expanded,onDismissRequest={expanded=false}){
                    choices.forEach { item ->
                        DropdownMenuItem(text={Text(item.company+" · "+item.role)},
                            onClick={expanded=false;onSwap(item.id)})
                    }
                }
            }
        }
        if(!c.complete) Text("Detailed verified job content is not ready; publishing remains locked.",
            color=Amber,fontSize=12.sp)
    }
}
@Composable private fun JobsPage(vm:AdminViewModel) {
    var query by remember { mutableStateOf("") }
    var filter by remember { mutableStateOf("All") }
    var input by remember { mutableStateOf("") }
    var publishing by remember { mutableStateOf(false) }
    val context=LocalContext.current
    val filtered=vm.jobs.filter{
        (filter=="All"||it.status.equals(filter,true))&&
        (it.role.contains(query,true)||it.company.contains(query,true))
    }
    LazyColumn(contentPadding=PaddingValues(16.dp),verticalArrangement=Arrangement.spacedBy(12.dp)){
        item{ CardSection("VIP job publishing","Add a single official job link") {
            OutlinedTextField(input,{input=it},label={Text("Official HTTPS job URL")},modifier=Modifier.fillMaxWidth())
            Button(onClick={vm.extract(input)},enabled=!vm.busy&&input.startsWith("https://")){Text("Extract job draft")}
            vm.manualDraft?.let {draft->
                Text(draft.optString("company")+" — "+draft.optString("role"),fontWeight=FontWeight.Bold)
                Text(draft.optString("desc").take(350),color=Gray,fontSize=12.sp)
                Text("Check the role, eligibility, description and official link before publishing.",
                    fontSize=12.sp,color=Amber)
                OutlinedButton(onClick={publishing=true}){Text("Review and submit VIP job")}
            }
        }}
        item{
            OutlinedTextField(query,{query=it},label={Text("Find existing jobs")},singleLine=true,
                modifier=Modifier.fillMaxWidth())
            Row(horizontalArrangement=Arrangement.spacedBy(8.dp)){
                listOf("All","Active","Expired").forEach { option ->
                    FilterChip(selected=filter==option,onClick={filter=option},label={Text(option)})
                }
            }
            Text("${filtered.size} matching jobs",color=Gray,fontSize=12.sp)
        }
        items(filtered.take(90),key={it.id}) { job ->
            CardSection(job.company,job.role) {
                Text(job.location,color=Gray,fontSize=12.sp)
                Text(job.status.replaceFirstChar{it.uppercase()},color=if(job.status=="active")Teal else Red,fontSize=12.sp)
                if(job.apply.startsWith("https://")) TextButton(onClick={
                    context.startActivity(Intent(Intent.ACTION_VIEW,Uri.parse(job.apply)))
                }){Text("Open official job")}
            }
        }
    }
    if(publishing) AlertDialog(onDismissRequest={publishing=false},
        title={Text("Submit VIP job?")},text={Text("Only publish if the extracted details are accurate and applications are open.")},
        confirmButton={TextButton(onClick={publishing=false;vm.publishManual()}){Text("Submit")}},
        dismissButton={TextButton(onClick={publishing=false}){Text("Cancel")}})
}
@Composable private fun MorePage(vm:AdminViewModel,onEnableBiometric:()->Unit,onRequestNotifications:()->Unit) {
    var screen by remember { mutableStateOf("more") }
    val context=LocalContext.current
    when(screen){
        "analytics"->AnalyticsPage(vm,onBack={screen="more"})
        "checker"->CheckerPage(vm,onBack={screen="more"})
        else -> LazyColumn(contentPadding=PaddingValues(16.dp),verticalArrangement=Arrangement.spacedBy(12.dp)) {
            item{CardSection("Reporting and Operations"){
                ListItem(headlineContent={Text("Website analytics")},supportingContent={Text("Traffic, conversions and top pages")},
                    leadingContent={Icon(Icons.Default.Insights,null)},modifier=Modifier.clickable{screen="analytics"})
                ListItem(headlineContent={Text("Expired job checker")},supportingContent={Text("Review uncertain listings conservatively")},
                    leadingContent={Icon(Icons.Default.VerifiedUser,null)},modifier=Modifier.clickable{screen="checker"})
            }}
            item{CardSection("Notifications","Firebase Cloud Messaging and daily reminders") {
                Text(vm.fcmStatus,color=if(vm.fcmStatus.startsWith("Registered"))Teal else Amber,fontSize=12.sp)
                OutlinedButton(onClick={onRequestNotifications}){Text("Allow Android notifications")}
                OutlinedButton(onClick=vm::connectPush){Text("Register device for FCM")}
                OutlinedButton(onClick=vm::testPush){Text("Send a test notification")}
                var reminderOn by remember {
                    mutableStateOf(context.getSharedPreferences("hd_review",0).getBoolean("reminder_enabled",true))
                }
                Row(verticalAlignment=Alignment.CenterVertically){
                    Text("Daily pending-review reminder",modifier=Modifier.weight(1f))
                    Switch(checked=reminderOn,onCheckedChange={reminderOn=it;vm.toggleReminder(it)})
                }
                Text("Android may deliver scheduled local reminders later under battery restrictions.",
                    color=Gray,fontSize=11.sp)
            }}
            item{CardSection("Security") {
                OutlinedButton(onClick=onEnableBiometric){Icon(Icons.Default.Fingerprint,null);Text("  Enable biometric unlock")}
                OutlinedButton(onClick={vm.logout()}){Text("Sign out and clear stored credentials")}
            }}
            item{CardSection("Website") {
                TextButton(onClick={context.startActivity(Intent(Intent.ACTION_VIEW,Uri.parse("https://hdcareers.in/admin/")))}) {
                    Text("Open HD Careers Web Admin ↗")
                }
                Text("Private Android build · Pixel optimized · Not distributed through Play Store",fontSize=11.sp,color=Gray)
            }}
        }
    }
}
@Composable private fun AnalyticsPage(vm:AdminViewModel,onBack:()->Unit) {
    LazyColumn(contentPadding=PaddingValues(16.dp),verticalArrangement=Arrangement.spacedBy(13.dp)){
        item{ TextButton(onClick=onBack){Icon(Icons.AutoMirrored.Filled.ArrowBack,null);Text("Analytics")}}
        item{ CardSection("Website performance","Responsive charts · actual GA4 data") {
            Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                listOf(1 to "24H",7 to "7D",30 to "30D").forEach { (num,label)->
                    FilterChip(selected=vm.days==num,onClick={vm.changeDays(num)},label={Text(label)})
                }
            }
            TwoMetricRows(listOf("Visitors" to "${vm.traffic.users}","Page views" to "${vm.traffic.views}",
                "Live" to "${vm.traffic.live}","Apply clicks" to "${vm.traffic.applies}",
                "Resume checks" to "${vm.traffic.resumes}"))
        }}
        item{BarList("Countries",vm.traffic.countries)}
        item{BarList("Popular pages",vm.traffic.pages)}
        item{BarList("Devices",vm.traffic.devices)}
    }
}
@Composable private fun BarList(title:String,rows:List<Pair<String,Int>>) {
    CardSection(title) {
        if(rows.isEmpty()) Text("No analytics available for this period.",color=Gray)
        val max=(rows.maxOfOrNull{it.second}?:1).coerceAtLeast(1)
        rows.forEach { (name,count)->
            Row(verticalAlignment=Alignment.CenterVertically) {
                Text(name.ifBlank{"Unknown"},modifier=Modifier.weight(1f),fontSize=12.sp,maxLines=2,overflow=TextOverflow.Ellipsis)
                Text("$count",fontWeight=FontWeight.Bold,fontSize=12.sp)
            }
            val animated by animateFloatAsState(targetValue=count.toFloat()/max,label="bar")
            LinearProgressIndicator(progress={animated},modifier=Modifier.fillMaxWidth().height(7.dp),
                color=Blue,trackColor=Pale,strokeCap=StrokeCap.Round)
        }
    }
}
@Composable private fun CheckerPage(vm:AdminViewModel,onBack:()->Unit) {
    val results=vm.checker.optJSONObject("results")
    val list=results?.optJSONArray("items")
    LazyColumn(contentPadding=PaddingValues(16.dp),verticalArrangement=Arrangement.spacedBy(12.dp)){
        item{TextButton(onClick=onBack){Icon(Icons.AutoMirrored.Filled.ArrowBack,null);Text("Expired job checker")}}
        item { CardSection("Conservative expiry checking") {
            Text("Blocked portals and CAPTCHA are not proof that a job expired.",color=Gray)
            Button(onClick=vm::checkerRun,enabled=!vm.busy){Text("Run checker")}
            Text("Review: ${results?.optInt("review")?:0} · Expired: ${results?.optInt("expired")?:0}",
                color=Gray)
        }}
        if(list!=null) items(list.length()) { index ->
            val j=list.optJSONObject(index)
            if(j!=null && j.optString("state")=="review") CardSection(
                j.optString("company","Unknown"),j.optString("role")) {
                Text(j.optString("reason"),fontSize=12.sp,color=Gray)
                val id=j.optInt("id",-1)
                Row {
                    OutlinedButton(onClick={vm.checkerResolve(id,"keep")},enabled=id>=0&&!vm.busy) {
                        Text("Keep live")
                    }
                    Spacer(Modifier.width(10.dp))
                    OutlinedButton(onClick={vm.checkerResolve(id,"expire")},enabled=id>=0&&!vm.busy) {
                        Text("Expire")
                    }
                }
            }
        }
    }
}
