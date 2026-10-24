package `in`.hdcareers.admin

import android.content.Intent
import android.net.Uri
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlin.math.max
import kotlinx.coroutines.delay

@Composable
fun PremiumAdminRoot(
    vm:AdminViewModel,
    onBiometricSignIn:()->Unit,
    onEnableBiometric:()->Unit,
    onRequestNotificationPermission:()->Unit
) {
    var moreOpen by remember { mutableStateOf(false) }
    // A preview belongs only to the current authenticated review session.
    var previewCandidateId by remember { mutableStateOf<String?>(null) }
    LaunchedEffect(vm.loggedIn) {
        if(!vm.loggedIn) previewCandidateId=null
    }
    val previewCandidate=if(vm.loggedIn) vm.batch.all.firstOrNull {
        it.id==previewCandidateId && it.approved
    } else null
    MaterialTheme(colorScheme=Brand.scheme,typography=Typography()) {
        if(!vm.loggedIn) {
            ProLogin(vm,onBiometricSignIn)
        } else {
            LaunchedEffect(vm.tab,moreOpen,vm.loggedIn) {
                while(vm.loggedIn && !moreOpen && vm.tab in listOf(0,2)) {
                    vm.refreshOperationsQuietly()
                    delay(30000)
                }
            }
            Scaffold(
                containerColor=Brand.background,
                topBar={
                    Surface(modifier=Modifier.fillMaxWidth().statusBarsPadding(),
                        color=Color.White,shadowElevation=1.dp) {
                        Row(Modifier.fillMaxWidth().padding(horizontal=16.dp,vertical=12.dp),
                            verticalAlignment=Alignment.CenterVertically,
                            horizontalArrangement=Arrangement.spacedBy(12.dp)) {
                            if(previewCandidate!=null) IconButton(onClick={previewCandidateId=null}) {
                                Icon(Icons.AutoMirrored.Filled.ArrowBack,"Back to review",tint=Brand.navy)
                            }
                            BrandLogo(39,false)
                            Column(Modifier.weight(1f)) {
                                Text("HD CAREERS",fontSize=10.sp,fontWeight=FontWeight.Black,
                                    letterSpacing=1.1.sp,color=Brand.blue)
                                Text(if(previewCandidate!=null)"Job Page Preview" else if(moreOpen)"Settings" else listOf("Today","Publish","Expiry","Jobs","Analytics")[vm.tab.coerceIn(0,4)],
                                    fontSize=19.sp,fontWeight=FontWeight.Black,color=Brand.navy)
                            }
                            if(previewCandidate==null) {
                            BadgedBox(badge={if(vm.pendingExpiryReviews.isNotEmpty() || (vm.batch.id.isNotBlank()&&vm.batch.reviewed<vm.batch.all.size))
                                Badge(containerColor=Brand.amber){} }) {
                                IconButton(onClick={moreOpen=false;vm.tab=if(vm.pendingExpiryReviews.isNotEmpty())2 else 1}) {
                                    Icon(Icons.Default.NotificationsNone,"Review notifications",tint=Brand.navy)
                                }
                            }
                            IconButton(onClick={moreOpen=!moreOpen}) {
                                Icon(Icons.Default.Settings,"Settings, Firebase and security",tint=Brand.navy)
                            }
                            IconButton(onClick={vm::refreshClicked}) {
                                Icon(Icons.Default.Refresh,"Refresh server data",tint=Brand.blue)
                            }
                            }
                        }
                    }
                },
                bottomBar={
                    if(previewCandidate==null) NavigationBar(containerColor=Color.White,tonalElevation=4.dp) {
                        val labels=listOf("Today","Publish","Expiry","Jobs","Analytics")
                        val symbols=listOf(Icons.Default.Dashboard,Icons.Default.FactCheck,
                            Icons.Default.Shield,Icons.Default.BusinessCenter,Icons.Default.Insights)
                        labels.forEachIndexed { index,label ->
                            NavigationBarItem(selected=vm.tab==index&&!moreOpen,onClick={vm.tab=index;moreOpen=false},
                                icon={Icon(symbols[index],contentDescription=label)},
                                label={Text(label,maxLines=1,fontSize=11.sp,fontWeight=FontWeight.SemiBold)},
                                colors=NavigationBarItemDefaults.colors(
                                    selectedIconColor=Brand.blue,selectedTextColor=Brand.navy,
                                    indicatorColor=Brand.sky,unselectedIconColor=Brand.gray,
                                    unselectedTextColor=Brand.gray))
                        }
                    }
                }
            ) { insets ->
                Box(Modifier.fillMaxSize().padding(insets)) {
                    if(previewCandidate!=null) {
                        ReviewedJobPagePreview(previewCandidate,vm.companyLogos,onBack={previewCandidateId=null})
                    } else if(moreOpen) ProMore(vm,onEnableBiometric,onRequestNotificationPermission) else when(vm.tab) {
                        0 -> ProHome(vm,onAnalytics={vm.tab=4})
                        1 -> ProReview(vm,onPreview={id->previewCandidateId=id;moreOpen=false})
                        2 -> ProChecker(vm,onBack={vm.tab=0})
                        3 -> ProJobs(vm)
                        else -> ProAnalyticsV2(vm)
                    }
                    if(vm.loading) LinearProgressIndicator(
                        modifier=Modifier.fillMaxWidth().align(Alignment.TopCenter),
                        color=Brand.blue,trackColor=Brand.sky)
                }
            }
        }
        if(vm.message.isNotBlank()) AlertDialog(
            onDismissRequest={vm.message=""},
            title={Text("HD Careers Admin",fontWeight=FontWeight.Bold)},
            text={Text(vm.message)},
            confirmButton={TextButton(onClick={vm.message=""}){Text("OK")}})
    }
}

@Composable
private fun ProLogin(vm:AdminViewModel,onBiometricSignIn:()->Unit) {
    var username by remember {mutableStateOf("")}
    var password by remember {mutableStateOf("")}
    Box(Modifier.fillMaxSize().background(Brand.background).statusBarsPadding()) {
        Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState())) {
            Box(Modifier.fillMaxWidth().height(270.dp).clip(RoundedCornerShape(bottomStart=34.dp,bottomEnd=34.dp))
                .background(Brush.linearGradient(listOf(Brand.navy,Brand.darkBlue,Brand.blue))),
                contentAlignment=Alignment.Center) {
                Column(horizontalAlignment=Alignment.CenterHorizontally,
                    verticalArrangement=Arrangement.spacedBy(12.dp)) {
                    BrandLogo(92)
                    Text("HD Careers Admin",fontSize=28.sp,color=Color.White,fontWeight=FontWeight.Black)
                    Text("Your private operations command center",fontSize=12.sp,
                        color=Color.White.copy(alpha=.74f))
                }
            }
            Column(Modifier.fillMaxWidth().padding(20.dp),
                verticalArrangement=Arrangement.spacedBy(14.dp)) {
                Text("Welcome back",fontSize=23.sp,color=Brand.navy,fontWeight=FontWeight.Black)
                Text("Sign in to manage jobs, analytics and approvals.",
                    color=Brand.gray,fontSize=13.sp)
                ProCard {
                    OutlinedTextField(username,{username=it},singleLine=true,
                        leadingIcon={Icon(Icons.Default.PersonOutline,null)},
                        label={Text("Admin username")},modifier=Modifier.fillMaxWidth(),
                        shape=RoundedCornerShape(14.dp))
                    OutlinedTextField(password,{password=it},singleLine=true,
                        visualTransformation=PasswordVisualTransformation(),
                        leadingIcon={Icon(Icons.Default.Lock,null)},
                        label={Text("Password")},modifier=Modifier.fillMaxWidth(),
                        shape=RoundedCornerShape(14.dp))
                    Button(onClick={vm.login(username,password)},enabled=!vm.busy,
                        modifier=Modifier.fillMaxWidth().height(51.dp),
                        shape=RoundedCornerShape(14.dp)) {
                        Icon(Icons.Default.Login,null)
                        Spacer(Modifier.width(9.dp))
                        Text("Secure sign in",fontWeight=FontWeight.Bold)
                    }
                    if(vm.hasBiometric) OutlinedButton(onClick=onBiometricSignIn,
                        modifier=Modifier.fillMaxWidth()) {
                        Icon(Icons.Default.Fingerprint,null)
                        Spacer(Modifier.width(8.dp))
                        Text("Unlock with fingerprint")
                    }
                }
                Row(verticalAlignment=Alignment.CenterVertically,
                    horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                    Icon(Icons.Default.VerifiedUser,null,tint=Brand.green,
                        modifier=Modifier.size(17.dp))
                    Text("Only authenticated admins can publish jobs.",
                        color=Brand.gray,fontSize=12.sp)
                }
            }
        }
    }
}

@Composable
private fun ProHome(vm:AdminViewModel,onAnalytics:()->Unit) {
    val active=vm.jobs.count{it.status=="active"}
    val awaiting=vm.batch.priority.count{it.decision=="unreviewed"||it.decision.isBlank()}
    val pending=vm.pendingExpiryReviews
    LazyColumn(contentPadding=PaddingValues(start=16.dp,end=16.dp,top=18.dp,bottom=28.dp),
        verticalArrangement=Arrangement.spacedBy(15.dp)) {
        item {
            Column(verticalArrangement=Arrangement.spacedBy(4.dp)) {
                Text("Your command center",fontSize=23.sp,fontWeight=FontWeight.Black,color=Brand.navy)
                Text("Everything that matters to HD Careers, in one place.",
                    fontSize=12.sp,color=Brand.gray)
            }
        }
        item {
            ProHero("Operations dashboard","Everything important,\nunder control.",
                "Jobs, reviews and website performance at a glance.") {
                Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                    HeroMiniStat(active.toString(),"Live jobs",Modifier.weight(1f))
                    HeroMiniStat((awaiting+pending.size).toString(),"To review",Modifier.weight(1f))
                    HeroMiniStat("9:00","Discovery",Modifier.weight(1f))
                }
            }
        }
        item {
            val metrics=mutableListOf(
                MetricSpec("Published jobs",vm.jobs.size.toString(),Icons.Default.Work,Brand.blue),
                MetricSpec("Active listings",active.toString(),Icons.Default.CheckCircle,Brand.green)
            )
            if(vm.adminRole=="owner") {
                metrics.add(MetricSpec("Page views",vm.traffic.views.toString(),Icons.Default.Visibility,Brand.violet))
                metrics.add(MetricSpec("Apply clicks",vm.traffic.applies.toString(),Icons.Default.TouchApp,Brand.cyan))
            }
            MetricsGrid(metrics)
        }
        item {
            ProCard {
                SectionHead(Icons.Default.AssignmentTurnedIn,"Daily review",
                    "Priority 10 + Backup 10",Brand.blue,action={vm.tab=1})
                if(vm.batch.id.isEmpty()) {
                    Row(verticalAlignment=Alignment.CenterVertically) {
                        Icon(Icons.Default.HourglassTop,null,Modifier.size(24.dp),tint=Brand.amber)
                        Spacer(Modifier.width(10.dp))
                        Text("Awaiting the next verified job batch",fontSize=13.sp,
                            color=Brand.navy,modifier=Modifier.weight(1f))
                    }
                } else {
                    LinearProgressIndicator(progress={vm.batch.reviewed.toFloat()/
                        max(1,vm.batch.priority.size+vm.batch.backup.size)},
                        modifier=Modifier.fillMaxWidth().height(7.dp).clip(RoundedCornerShape(8.dp)),
                        color=Brand.blue,trackColor=Brand.sky)
                    Text(vm.batch.reviewed.toString()+" of "+
                        (vm.batch.priority.size+vm.batch.backup.size)+" jobs reviewed",
                        fontSize=12.sp,color=Brand.gray)
                }
                Button(onClick={vm.tab=1},modifier=Modifier.fillMaxWidth(),
                    shape=RoundedCornerShape(13.dp)) {
                    Text("Open review center")
                    Spacer(Modifier.width(8.dp))
                    Icon(Icons.Default.ArrowForward,null,Modifier.size(16.dp))
                }
            }
        }
        item {
            ProCard {
                SectionHead(Icons.Default.WarningAmber,"Expiry checker · pending reviews",
                    if(pending.isEmpty())"No unresolved job checks" else pending.size.toString()+" jobs waiting for your decision",
                    if(pending.isEmpty())Brand.green else Brand.amber,action={vm.tab=2})
                if(pending.isEmpty()) {
                    Row(verticalAlignment=Alignment.CenterVertically,
                        horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                        Icon(Icons.Default.CheckCircle,null,tint=Brand.green,modifier=Modifier.size(21.dp))
                        Text("All reported checks are clear. Run or refresh to check again.",
                            color=Brand.gray,fontSize=12.sp)
                    }
                } else {
                    pending.take(4).forEach { item ->
                        Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically,
                            horizontalArrangement=Arrangement.spacedBy(9.dp)) {
                            Icon(Icons.Default.WarningAmber,null,tint=Brand.amber,
                                modifier=Modifier.size(19.dp))
                            Column(Modifier.weight(1f)) {
                                Text(item.optString("company","Employer"),fontWeight=FontWeight.Bold,
                                    color=Brand.navy,fontSize=12.sp,maxLines=1)
                                Text(item.optString("role","Review needed"),
                                    color=Brand.gray,fontSize=11.sp,maxLines=2)
                            }
                            Icon(Icons.Default.ChevronRight,null,tint=Brand.gray)
                        }
                        HorizontalDivider(color=Brand.outline)
                    }
                    if(pending.size>4) Text("+"+(pending.size-4)+" more waiting in Expiry",
                        color=Brand.gray,fontSize=11.sp)
                }
                Button(onClick={vm.tab=2},modifier=Modifier.fillMaxWidth(),
                    shape=RoundedCornerShape(13.dp)) {
                    Text(if(pending.isEmpty())"Open job checker" else "Review "+pending.size+" pending jobs")
                    Spacer(Modifier.width(7.dp))
                    Icon(Icons.Default.ArrowForward,null,modifier=Modifier.size(16.dp))
                }
            }
        }
        if(vm.adminRole=="owner") item {
            ProCard {
                SectionHead(Icons.Default.ShowChart,"Traffic trend",
                    "Real Google Analytics data · "+vm.days+" day view",Brand.cyan,
                    action=onAnalytics)
                if(vm.traffic.trend.isNotEmpty()) {
                    TrendSpark(vm.traffic.trend,accent=Brand.cyan)
                } else Text("Traffic history will appear when GA4 returns daily measurements.",
                    color=Brand.gray,fontSize=12.sp)
                Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                    ProPill(vm.traffic.users.toString()+" visitors",Brand.blue)
                    ProPill(vm.traffic.live.toString()+" live",Brand.green)
                }
            }
        }
        item {
            ProCard {
                SectionHead(Icons.Default.AutoAwesome,"Quick actions","Your most-used admin tools")
                Row(horizontalArrangement=Arrangement.spacedBy(10.dp)) {
                    QuickAction("Review",Icons.Default.FactCheck,Brand.blue,Modifier.weight(1f)){vm.tab=1}
                    QuickAction("Expiry",Icons.Default.Shield,Brand.amber,Modifier.weight(1f)){vm.tab=2}
                    QuickAction("Jobs",Icons.Default.BusinessCenter,Brand.violet,Modifier.weight(1f)){vm.tab=3}
                }
            }
        }
    }
}
@Composable private fun QuickAction(label:String,icon:androidx.compose.ui.graphics.vector.ImageVector,
    accent:Color,modifier:Modifier=Modifier,onClick:()->Unit) {
    Surface(onClick=onClick,modifier=modifier,shape=RoundedCornerShape(13.dp),
        color=accent.copy(alpha=.075f)) {
        Column(Modifier.padding(vertical=14.dp),horizontalAlignment=Alignment.CenterHorizontally,
            verticalArrangement=Arrangement.spacedBy(7.dp)) {
            Icon(icon,null,Modifier.size(23.dp),tint=accent)
            Text(label,fontSize=11.sp,fontWeight=FontWeight.Bold,color=Brand.navy)
        }
    }
}
@Composable
private fun ProReview(vm:AdminViewModel,onPreview:(String)->Unit) {
    var selected by remember { mutableIntStateOf(0) }
    var confirm by remember { mutableStateOf(false) }
    val chosen=vm.batch.all.filter { it.id in vm.selectedIds && it.id !in vm.publishedReviewIds }
    val raw=when(selected) {
        0 -> vm.batch.priority.filterNot { it.id in vm.selectedIds || it.decision=="expired" || it.id in vm.publishedReviewIds }
        1 -> vm.batch.backup.filterNot { it.id in vm.selectedIds || it.decision=="expired" || it.id in vm.publishedReviewIds }
        2 -> chosen
        else -> vm.batch.all.filter { it.decision=="expired" || it.id in vm.publishedReviewIds }
    }
    val candidates=if(selected==2||selected==3)raw else raw.sortedWith(compareBy<Candidate> {
        when(it.decision) { "live" -> 0; "unreviewed", "" -> 1; "unsure" -> 2; else -> 3 }
    }.thenByDescending { it.complete })
    val total=vm.batch.all.size
    val ctx=LocalContext.current
    LaunchedEffect(vm.tab,vm.batch.status) {
        if(vm.tab==1 && vm.batch.status=="submitted") {
            while(true) {
                vm.refreshPublishingStatusQuietly()
                delay(10000)
            }
        }
    }
    LazyColumn(modifier=Modifier.fillMaxSize().pointerInput(selected) {
        var swipe=0f
        detectHorizontalDragGestures(
            onDragStart={swipe=0f},
            onHorizontalDrag={change,delta->change.consume();swipe+=delta},
            onDragEnd={
                if(swipe < -80f) selected=(selected+1).coerceAtMost(3)
                if(swipe > 80f) selected=(selected-1).coerceAtLeast(0)
            }
        )
    },contentPadding=PaddingValues(16.dp),verticalArrangement=Arrangement.spacedBy(13.dp)) {
        item {
            ProHero("Daily publishing","Review. Select.\nPublish.",
                "Priority and Backup are for review. Verified Live jobs move into Publish Ready.",
                icon=Icons.Default.FactCheck) {
                Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                    HeroMiniStat(vm.batch.priority.size.toString(),"Priority",Modifier.weight(1f))
                    HeroMiniStat(vm.batch.backup.size.toString(),"Backup",Modifier.weight(1f))
                    HeroMiniStat(chosen.size.toString()+"/10","Publish Ready",Modifier.weight(1f))
                }
            }
        }
        item {
            ProCard {
                SectionHead(Icons.Default.FactCheck,"Your review desk","Swipe sideways to switch sections")
                LinearProgressIndicator(
                    progress={vm.batch.reviewed.toFloat()/max(1,total)},
                    modifier=Modifier.fillMaxWidth().height(7.dp).clip(RoundedCornerShape(8.dp)),
                    color=Brand.blue,trackColor=Brand.sky)
                Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                    HeroMiniStat(vm.batch.reviewed.toString(),"Reviewed",Modifier.weight(1f))
                    HeroMiniStat(vm.batch.expiredCount.toString(),"Expired",Modifier.weight(1f))
                    HeroMiniStat(vm.batch.readyCount.toString(),"Content Ready",Modifier.weight(1f))
                }
                Text("${vm.batch.uniqueEmployers} employers · ${vm.batch.all.size} candidates · Details needing attention: ${vm.batch.incomplete}",
                    fontSize=12.sp,color=Brand.gray)
                TabRow(selectedTabIndex=selected,containerColor=Color.Transparent,
                    contentColor=Brand.blue) {
                    listOf("Priority","Backup","Ready","History").forEachIndexed {index,label->
                        Tab(selected=selected==index,onClick={selected=index},
                            text={Text(if(index==2)"Ready (${chosen.size})" else label,
                                fontWeight=FontWeight.Bold,fontSize=11.sp,maxLines=1)})
                    }
                }
                Text(when(selected){
                    0 -> "Expired and website-confirmed published jobs move to History; no data is deleted."
                    1 -> "Backup: Live roles here can also go directly to Publish Ready."
                    2 -> "Final review: only complete, verified jobs can be published."
                    else -> "Read-only reviewed job history and verified delivery evidence."
                },fontSize=11.sp,color=Brand.gray)
            }
        }
        if(vm.twoJobInbox.optJSONObject("staged")!=null) {
        item {
            ProCard {
                SectionHead(Icons.Default.NotificationsActive,"Two-job review & live tracker","Independent of your daily batch")
                LaunchedEffect(vm.twoJobInbox.optJSONObject("staged")?.optString("status"),vm.tab) {
                    if(vm.tab==1 && vm.twoJobInbox.optJSONObject("staged")?.optString("status")=="submitted"){
                        while(true){vm.refreshTwoJobInboxQuietly();delay(10000)}
                    }
                }
                val inbox=vm.twoJobInbox.optJSONObject("staged")
                val entries=inbox?.optJSONArray("jobs")
                val submitted=inbox?.optString("status")=="submitted"
                val statuses=vm.twoJobInbox.optJSONArray("stages")
                if(entries==null) Text("Refresh to load the separate two-job test inbox.",fontSize=12.sp,color=Brand.gray)
                else {
                    Text("Two official-source job drafts · "+(if(submitted)"Publishing submitted" else "Awaiting your review"),fontSize=12.sp,color=Brand.gray)
                    for(n in 0 until entries.length()){
                        val job=entries.optJSONObject(n) ?: continue
                        val id=job.optString("id")
                        var expanded by remember(id){mutableStateOf(false)}
                        HorizontalDivider()
                        Column(Modifier.fillMaxWidth().clickable{expanded=!expanded}.padding(vertical=6.dp)) {
                            Text(job.optString("company")+" · "+job.optString("role"),fontWeight=FontWeight.Bold,fontSize=13.sp)
                            Text("Review: "+job.optString("reviewedStatus")+"  •  Tap for individual status",fontSize=11.sp,color=Brand.gray)
                        }
                        if(expanded){
                            val ctx=LocalContext.current
                            val uri=job.optString("apply")
                            TextButton(onClick={if(uri.startsWith("https://"))ctx.startActivity(Intent(Intent.ACTION_VIEW,Uri.parse(uri)))}) {Text("Open exact official job")}
                            Text("Job overview: "+job.optString("desc"),fontSize=12.sp,color=Brand.gray,lineHeight=18.sp)
                            Text("Eligibility: "+job.optString("elig"),fontSize=12.sp,color=Brand.gray,lineHeight=18.sp)
                            if(!submitted){
                                Row(horizontalArrangement=Arrangement.spacedBy(6.dp)){
                                    OutlinedButton(onClick={vm.reviewTestJob(id,"live")},enabled=!vm.busy){Text("Live")}
                                    OutlinedButton(onClick={vm.reviewTestJob(id,"expired")},enabled=!vm.busy){Text("Expired")}
                                    OutlinedButton(onClick={vm.reviewTestJob(id,"unsure")},enabled=!vm.busy){Text("Unsure")}
                                }
                                val chosen=id in vm.twoJobSelected
                                Row(verticalAlignment=Alignment.CenterVertically){
                                    Checkbox(checked=chosen,onCheckedChange={vm.selectTestJob(id,it)},enabled=job.optString("reviewedStatus")=="live"&&!vm.busy)
                                    Text("Select verified Live job for publishing",fontSize=12.sp)
                                }
                            }else{
                                val stage=(0 until (statuses?.length() ?: 0)).mapNotNull{statuses?.optJSONObject(it)}
                                    .firstOrNull{it.optString("candidateId")==id}
                                listOf("GitHub" to (stage?.optString("github")?:"dispatched-unconfirmed"),
                                    "Website" to (stage?.optString("website")?:"unconfirmed"),
                                    "Telegram" to (stage?.optString("telegram")?:"unconfirmed")).forEach{(label,value)->
                                    Row(Modifier.fillMaxWidth().padding(vertical=7.dp),horizontalArrangement=Arrangement.SpaceBetween){
                                        Text(label,fontWeight=FontWeight.Bold,fontSize=12.sp)
                                        Text(value,fontSize=12.sp,color=if(value=="live"||value=="delivered")Brand.green else Brand.amber)
                                    }
                                }
                                stage?.optString("telegramMessageId")?.takeIf{it.isNotBlank()}?.let{
                                    Text("Telegram message ID: "+it,fontSize=11.sp,color=Brand.gray)
                                }
                                Text("Verified updates refresh every 10 seconds. Dispatch acceptance is not proof of delivery.",fontSize=11.sp,color=Brand.gray)
                            }
                        }
                    }
                }
                Row(horizontalArrangement=Arrangement.spacedBy(8.dp)){
                    OutlinedButton(onClick=vm::loadTwoJobInbox,enabled=!vm.busy){Text("Refresh")}
                    if(entries==null) Button(onClick=vm::stageTwoJobInbox,enabled=!vm.busy){Text("Stage 2 jobs")}
                    if(!submitted && entries!=null) Button(onClick=vm::replaceTwoJobInbox,enabled=!vm.busy){Text("Clear & load 2 new jobs")}
                }
                if(!submitted&&vm.twoJobSelected.isNotEmpty()) {
                    var confirmTest by remember {mutableStateOf(false)}
                    Button(onClick={confirmTest=true},enabled=!vm.busy,modifier=Modifier.fillMaxWidth()){Text("Publish ${vm.twoJobSelected.size} verified test job(s)")}
                    if(confirmTest) AlertDialog(onDismissRequest={confirmTest=false},
                        title={Text("Publish selected real jobs?")},
                        text={Text("This publishes selected Live jobs on HD Careers and posts them to Telegram. Continue only after verifying each exact official Apply link.")},
                        confirmButton={TextButton(onClick={confirmTest=false;vm.publishTestJobs()}){Text("Confirm Publish")}},
                        dismissButton={TextButton(onClick={confirmTest=false}){Text("Cancel")}})
                }
                Text("Each job shows independent GitHub/data, website and Telegram evidence after submission.",fontSize=11.sp,color=Brand.gray)
            }
        }
        }
        if(vm.batch.id.isBlank()) item {
            ProEmpty(Icons.Default.EventNote,"No batch available",
                "The discovery pipeline must generate real source-backed jobs first.",
                "Refresh now",vm::refreshClicked)
        } else if(candidates.isEmpty()) item {
            ProEmpty(Icons.Default.CheckCircle,
                if(selected==2)"Nothing in Publish Ready" else if(selected==3)"History is empty" else "No jobs remaining in this section",
                if(selected==2)"Verify a role Live and add it from Priority or Backup."
                else if(selected==3)"Expired and confirmed published jobs appear in History."
                else "Reviewed jobs have moved to Publish Ready or History.",
                "Refresh",vm::refreshClicked)
        }
        itemsIndexed(candidates,key={_,item->item.id}) {i,job->
            if(selected==3){
                ProCard {
                    Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text(job.company,fontWeight=FontWeight.Black,fontSize=14.sp,color=Brand.navy)
                            Text(job.role,fontSize=12.sp,color=Brand.gray)
                        }
                        ProPill(if(job.decision=="expired")"EXPIRED" else "WEBSITE LIVE",
                            if(job.decision=="expired")Brand.red else Brand.green)
                    }
                    Text("Original decision and publishing evidence retained.",fontSize=11.sp,color=Brand.gray)
                    if(job.apply.startsWith("https://")) TextButton(onClick={
                        ctx.startActivity(Intent(Intent.ACTION_VIEW,Uri.parse(job.apply)))
                    }){ Icon(Icons.Default.OpenInNew,null,Modifier.size(16.dp)); Text(" Official source") }
                }
            } else ProCandidateCard(job,i,selected==0,vm.companyLogos,vm.busy,
                chosen=job.id in vm.selectedIds,published=job.id in vm.publishedReviewIds,
                inReady=selected==2,preview={onPreview(job.id)},decide={vm.decide(job.id,it)},
                 verifyAndAdd={vm.verifyAndAdd(job.id)},
                toggle={vm.toggleSelected(job.id,it)})
        }
        if(vm.batch.id.isNotBlank() && (selected==2||selected==3)) item {
            ProCard {
                SectionHead(Icons.Default.RocketLaunch,"Publish Ready",
                    "Review your selected jobs before final confirmation",Brand.green)
                val submitted=vm.batch.status=="submitted"||vm.batch.status=="published"
                val progress=vm.publishingProgress
                val stages=progress.optJSONArray("stages")
                val count=stages?.length() ?: 0
                if(submitted){
                    Text("Approved batch submitted · "+count+" jobs in the publishing tracker",
                        color=Brand.green,fontWeight=FontWeight.Bold,fontSize=13.sp)
                    Text("No action needed. Your previous confirmation is protected from duplicate publishing.",
                        color=Brand.gray,fontSize=12.sp,lineHeight=18.sp)
                }else if(selected==2){
                    val incomplete=chosen.filterNot { it.approved }
                    Text("${chosen.size} of 10 selected · ${incomplete.size} awaiting source details",
                        color=if(incomplete.isEmpty())Brand.green else Brand.amber,fontSize=12.sp)
                    if(incomplete.isNotEmpty()) {
                        Text("Job details are recovered from official sources before publication.",
                            fontSize=12.sp,color=Brand.gray,lineHeight=18.sp)
                    }
                    if(!vm.canPublish) vm.selectedBlockers.take(4).forEach { reason ->
                        Text("• "+reason,fontSize=12.sp,color=Brand.amber,lineHeight=17.sp)
                    }
                    Button(onClick={confirm=true},enabled=vm.canPublish&&!vm.busy,
                        modifier=Modifier.fillMaxWidth(),shape=RoundedCornerShape(14.dp)) {
                        Icon(Icons.Default.Send,null)
                        Spacer(Modifier.width(8.dp))
                        Text("Verify & Publish ${chosen.size} job(s)")
                    }
                }
                HorizontalDivider(color=Brand.sky)
                SectionHead(Icons.Default.Route,"Live publishing pipeline","Refreshes every 10 seconds after approval",Brand.blue)
                val pipeline=progress.optJSONObject("pipeline")
                val gh=progress.optJSONObject("workflow")
                val ghStatus=gh?.optString("conclusion")?.takeUnless{it.isBlank()||it=="null"}
                    ?:gh?.optString("state")?.takeUnless{it.isBlank()||it=="null"}
                    ?:"Awaiting verified workflow data"
                val tracked=count>0
                ProPipelineStep("01","Owner approval",
                    if(submitted)"complete" else "pending",
                    if(submitted)"Both review and publishing request submitted" else "Awaiting final review")
                ProPipelineStep("02","GitHub publishing",
                    if(ghStatus=="success")"complete" else if(ghStatus=="failure")"failed" else "pending",
                    if(tracked)ghStatus else "No submitted workflow yet")
                ProPipelineStep("03","Website content",
                    if(progress.optInt("dataCommittedCount")==count&&count>0)"complete" else "pending",
                    "${progress.optInt("dataCommittedCount")} of $count job records committed")
                ProPipelineStep("04","Live production website",
                    if(progress.optInt("publishedCount")==count&&count>0)"complete" else "pending",
                    "${progress.optInt("publishedCount")} of $count pages independently confirmed live")
                ProPipelineStep("05","Hourly Telegram",
                    if(progress.optInt("telegramDelivered")==count&&count>0)"complete"
                    else if(progress.optInt("telegramHourlyPending")>0)"queued" else "pending",
                    "${progress.optInt("telegramHourlyPending")} queued · ${progress.optInt("telegramDelivered")} delivered")
                if((gh?.optLong("runId",0L) ?: 0L)>0L){
                    val runLink=gh?.optString("url").orEmpty()
                    if(runLink.startsWith("https://")) TextButton(onClick={
                        ctx.startActivity(Intent(Intent.ACTION_VIEW,Uri.parse(runLink)))
                    }){Icon(Icons.Default.OpenInNew,null);Spacer(Modifier.width(5.dp));Text("Open verified GitHub workflow")}
                }
                Text("Latest server check: "+progress.optString("observedAt").takeIf{it.isNotBlank()}?.replace("T"," ")?.take(19).orEmpty()+" UTC",
                    fontSize=11.sp,color=Brand.gray)
                OutlinedButton(onClick=vm::refreshPublishingStatus,enabled=!vm.busy,
                    modifier=Modifier.fillMaxWidth(),shape=RoundedCornerShape(13.dp)) {
                    Icon(Icons.Default.Refresh,null)
                    Spacer(Modifier.width(8.dp))
                    Text("Refresh verified status")
                }
                if(tracked) {
                    HorizontalDivider(color=Brand.sky)
                    Text("INDIVIDUAL JOB STATUS",fontWeight=FontWeight.Black,
                        fontSize=11.sp,letterSpacing=1.sp,color=Brand.blue)
                    for(i in 0 until count){
                        val stage=stages?.optJSONObject(i) ?: continue
                        val id=stage.optString("candidateId")
                        var expanded by remember(id) {mutableStateOf(true)}
                        val company=stage.optString("company")
                        val title=stage.optString("role")
                        val queueStatus=stage.optString("telegram","not_queued")
                        Surface(color=Color.White,shape=RoundedCornerShape(18.dp),
                            border=androidx.compose.foundation.BorderStroke(1.dp,
                                if(queueStatus=="delivered")Brand.green.copy(alpha=.55f) else Brand.outline),
                            shadowElevation=3.dp) {
                            Column(Modifier.fillMaxWidth().animateContentSize().padding(13.dp),
                                verticalArrangement=Arrangement.spacedBy(9.dp)) {
                                Row(Modifier.fillMaxWidth().clickable{expanded=!expanded},
                                    verticalAlignment=Alignment.CenterVertically,
                                    horizontalArrangement=Arrangement.spacedBy(9.dp)){
                                    Icon(if(queueStatus=="delivered")Icons.Default.CheckCircle else Icons.Default.WorkOutline,
                                        null,tint=if(queueStatus=="delivered")Brand.green else Brand.blue)
                                    Column(Modifier.weight(1f)){
                                        Text(company,fontWeight=FontWeight.Black,fontSize=15.sp,color=Brand.navy)
                                        Text(title,fontSize=11.sp,color=Brand.gray,maxLines=2)
                                    }
                                    ProPill(if(queueStatus=="delivered")"SENT" else if(queueStatus=="uncertain")"CHECK" else "TRACKING",
                                         if(queueStatus=="delivered")Brand.green else if(queueStatus=="uncertain")Brand.red else Brand.blue)
                                     Icon(if(expanded)Icons.Default.ExpandLess else Icons.Default.ExpandMore,null,tint=Brand.blue)
                                }
                                if(expanded){
                                    Row(horizontalArrangement=Arrangement.spacedBy(6.dp)) {
                                        ProPill(if(ghStatus=="success")"GitHub complete" else "GitHub pending",Brand.blue)
                                        ProPill(if(stage.optString("website")=="live")"Site live" else "Deploying",
                                            if(stage.optString("website")=="live")Brand.green else Brand.amber)
                                    }
                                    ProPipelineStep("1","GitHub",
                                        if(ghStatus=="success")"complete" else if(ghStatus=="failure")"failed" else "pending",
                                        if(ghStatus=="success")"Exact workflow completed successfully" else ghStatus)
                                    ProPipelineStep("2","Data saved",
                                        if(stage.optString("website") in listOf("live","data-committed"))"complete" else "pending",
                                        if(stage.optString("website") in listOf("live","data-committed"))"Job page generated in repository" else "Not confirmed")
                                    val siteLive=stage.optString("website")=="live"
                                    ProPipelineStep("3","Public website",
                                        if(siteLive)"complete" else "pending",
                                        if(siteLive)"Official job page responded with matching Apply URL" else "Awaiting live-page verification")
                                    val pos=stage.optInt("queuePosition",0)
                                    ProPipelineStep("4","Telegram hourly queue",
                                        if(queueStatus=="delivered")"complete" else if(queueStatus in listOf("pending","sending"))"queued" else "pending",
                                        when(queueStatus){
                                            "delivered"->"Message confirmed delivered"
                                            "sending"->"Claimed and sending"
                                            "pending"->"Position "+(if(pos>0)pos.toString() else "pending")+" · one eligible job per hour"
                                            "uncertain"->"Delivery uncertain — manual inspection required"
                                            else->"Not yet queued"
                                        })
                                    val dueAt=stage.optString("telegramDueAt")
                                    if(dueAt.isNotBlank()&&dueAt!="null"&&queueStatus!="delivered")
                                        Text("Telegram target: "+dueAt.replace("T"," ").take(19)+" UTC",
                                            fontWeight=FontWeight.Bold,fontSize=12.sp,color=Brand.blue)
                                    val submittedAt=stage.optString("queuedAt")
                                    if(submittedAt.isNotBlank()&&submittedAt!="null")
                                        Text("Queued: "+submittedAt.replace("T"," ").take(19)+" UTC",
                                            fontSize=11.sp,color=Brand.gray)
                                    val deliveredAt=stage.optString("telegramDeliveredAt")
                                    if(deliveredAt.isNotBlank()&&deliveredAt!="null")
                                        Text("Delivered: "+deliveredAt.replace("T"," ").take(19)+" UTC",
                                            fontSize=11.sp,color=Brand.green)
                                    val messageId=stage.optString("telegramMessageId")
                                    if(messageId.isNotBlank()&&messageId!="null") {
                                        Text("Telegram message #"+messageId,fontSize=11.sp,color=Brand.green)
                                        TextButton(onClick={ctx.startActivity(Intent(Intent.ACTION_VIEW,
                                            Uri.parse("https://t.me/HD_Careers/"+messageId)))}) {
                                            Icon(Icons.Default.Send,null,Modifier.size(15.dp))
                                            Text(" View confirmed Telegram post")
                                        }
                                    }
                                    val pageUrl=stage.optString("pageUrl")
                                    if(pageUrl.startsWith("https://")) TextButton(onClick={
                                        ctx.startActivity(Intent(Intent.ACTION_VIEW,Uri.parse(pageUrl)))
                                    }) {
                                        Icon(Icons.Default.OpenInNew,null,modifier=Modifier.size(16.dp))
                                        Spacer(Modifier.width(5.dp))
                                        Text("Open HD Careers job page")
                                    }
                                }
                            }
                        }
                    }
                }else if(submitted){
                    Text("Server details unavailable. The batch has already been submitted; do not publish it again.",
                        color=Brand.amber,fontSize=12.sp,lineHeight=18.sp)
                }
                Text("GitHub completion, website availability, and Telegram message IDs are verified separately. A GitHub commit does not prove delivery.",
                    fontSize=11.sp,color=Brand.gray,lineHeight=17.sp)
            }
        }
    }
    if(confirm) AlertDialog(onDismissRequest={confirm=false},
        title={Text("Publish ${chosen.size} verified job(s)?",fontWeight=FontWeight.Black)},
        text={Text("Send these complete jobs to GitHub. Website deployment and Telegram delivery will be tracked separately, without claiming success early.")},
        confirmButton={TextButton(onClick={confirm=false;vm.publishBatch()}){Text("Confirm & Start")}},
        dismissButton={TextButton(onClick={confirm=false}){Text("Cancel")}})
}

@Composable
private fun ProPipelineStep(number:String,title:String,state:String,detail:String) {
    val good=state=="complete"
    val failed=state=="failed"
    val color=if(good)Brand.green else if(failed)Brand.red else if(state=="queued")Brand.blue else Brand.gray
    Row(Modifier.fillMaxWidth().padding(vertical=2.dp),
        horizontalArrangement=Arrangement.spacedBy(11.dp),verticalAlignment=Alignment.CenterVertically) {
        Surface(shape=RoundedCornerShape(12.dp),
            color=color.copy(alpha=.12f),modifier=Modifier.size(34.dp)) {
            Box(contentAlignment=Alignment.Center) {
                if(good)Icon(Icons.Default.Check,null,tint=color,modifier=Modifier.size(19.dp))
                else if(failed)Icon(Icons.Default.ErrorOutline,null,tint=color,modifier=Modifier.size(19.dp))
                else Text(number,color=color,fontWeight=FontWeight.Bold,fontSize=11.sp)
            }
        }
        Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(2.dp)) {
            Text(title,fontWeight=FontWeight.SemiBold,fontSize=13.sp,color=Brand.navy)
            Text(detail,fontSize=11.sp,color=Brand.gray,lineHeight=16.sp)
        }
        Text(when(state){"complete"->"Done";"failed"->"Failed";"queued"->"Queued";else->"Pending"},
            fontSize=10.sp,fontWeight=FontWeight.Bold,color=color)
    }
}

@Composable
private fun ProCandidateCard(c:Candidate,index:Int,priority:Boolean,
    logos:Map<String,CompanyLogoSource>,busy:Boolean,
    chosen:Boolean,published:Boolean,inReady:Boolean,
    preview:()->Unit,decide:(String)->Unit,verifyAndAdd:()->Unit,toggle:(Boolean)->Unit) {
    val ctx=LocalContext.current
    val category=when(c.group) {"nonit"->"Non-IT";"training"->"Internship / Apprentice";else->"Fresher IT"}
    val decisionColor=when(c.decision) {
        "live"->Brand.green;"expired"->Brand.red;"unsure"->Brand.amber;else->Brand.blue
    }
    ProCard {
        Row(verticalAlignment=Alignment.Top,horizontalArrangement=Arrangement.spacedBy(12.dp)) {
            CompanyMark(c.company,logos,c.job,45)
            Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(3.dp)) {
                Text(c.company,fontWeight=FontWeight.ExtraBold,color=Brand.navy,fontSize=14.sp)
                Text(c.role,fontWeight=FontWeight.Bold,color=Brand.navy,fontSize=13.sp,lineHeight=18.sp)
                Text(listOf(c.location,c.experience).filter{it.isNotBlank()}.joinToString(" · "),
                    fontSize=11.sp,color=Brand.gray)
            }
            Text("#"+(index+1),color=Brand.gray,fontSize=11.sp,fontWeight=FontWeight.Bold)
        }
        Row(horizontalArrangement=Arrangement.spacedBy(7.dp)) {
            ProPill(category,Brand.blue)
            ProPill(c.decision.ifBlank{"Needs review"}.replaceFirstChar{it.uppercase()},decisionColor)
            if(inReady) ProPill("Selected",Brand.green)
        }
        if(c.approved && !published) OutlinedButton(
            onClick=preview,enabled=!busy,modifier=Modifier.fillMaxWidth(),
            shape=RoundedCornerShape(12.dp)
        ) {
            Icon(Icons.Default.Visibility,"Preview candidate job page",Modifier.size(17.dp))
            Spacer(Modifier.width(7.dp))
            Text("Preview job page",fontSize=12.sp,fontWeight=FontWeight.Bold)
        }
        if(c.apply.startsWith("https://")) TextButton(onClick={
            ctx.startActivity(Intent(Intent.ACTION_VIEW,Uri.parse(c.apply)))
        }) {
            Icon(Icons.Default.OpenInNew,null,Modifier.size(15.dp))
            Spacer(Modifier.width(5.dp))
            Text("Open official application",fontSize=12.sp,fontWeight=FontWeight.Bold)
        }
        Row(horizontalArrangement=Arrangement.spacedBy(6.dp)) {
            listOf("live","expired","unsure").forEach{status->
                val color=when(status){"live"->Brand.green;"expired"->Brand.red;else->Brand.amber}
                OutlinedButton(onClick={decide(status)},enabled=!busy,
                    shape=RoundedCornerShape(11.dp),contentPadding=PaddingValues(horizontal=8.dp),
                    modifier=Modifier.weight(1f).height(37.dp),
                    colors=ButtonDefaults.outlinedButtonColors(
                        containerColor=if(status==c.decision) color.copy(alpha=.10f) else Color.White),
                    border=androidx.compose.foundation.BorderStroke(1.dp,
                        if(status==c.decision)color.copy(alpha=.5f) else Brand.outline)) {
                    Text(status.replaceFirstChar{it.uppercase()},fontWeight=FontWeight.Bold,
                        fontSize=10.sp,color=color,maxLines=1)
                }
            }
        }
        if(inReady) {
            OutlinedButton(onClick={toggle(false)},enabled=!busy,modifier=Modifier.fillMaxWidth()) {
                Icon(Icons.Default.ArrowBack,null,Modifier.size(17.dp))
                Spacer(Modifier.width(6.dp))
                Text("Remove from Publish Ready")
            }
        } else if(!published) {
            Button(onClick={if(c.selectable)toggle(true) else verifyAndAdd()},enabled=!busy&&c.apply.startsWith("https://"),
                modifier=Modifier.fillMaxWidth(),shape=RoundedCornerShape(12.dp)) {
                Icon(Icons.Default.Add,null,Modifier.size(17.dp))
                Spacer(Modifier.width(6.dp))
                Text(if(c.selectable)"Add to Publish Ready" else "Verified official link · Add")
            }
        } else Text("Already published",fontSize=12.sp,color=Brand.green)
        if(c.decision=="live"&&!c.approved) {
            Text("Source details needed before publishing: "+c.missingDetails.joinToString(", "),
                fontSize=11.sp,color=Brand.amber,lineHeight=16.sp)
        }
    }
}

@Composable
private fun ProJobs(vm:AdminViewModel) {
    var query by remember{mutableStateOf("")}
    var filter by remember{mutableStateOf("All")}
    var link by remember{mutableStateOf("")}
    var askPublish by remember{mutableStateOf(false)}
    val ctx=LocalContext.current
    val filtered=vm.jobs.filter {
        (filter=="All"||it.status.equals(filter,true))&&
            (it.role.contains(query,true)||it.company.contains(query,true))
    }
    LazyColumn(contentPadding=PaddingValues(16.dp),verticalArrangement=Arrangement.spacedBy(13.dp)) {
        item {
            ProHero("Job management","Publish smarter.\nManage faster.",
                "All your existing listings and VIP publishing controls.",icon=Icons.Default.BusinessCenter) {
                Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                    HeroMiniStat(vm.jobs.size.toString(),"Total jobs",Modifier.weight(1f))
                    HeroMiniStat(vm.jobs.count{it.status=="active"}.toString(),"Active",Modifier.weight(1f))
                    HeroMiniStat(vm.jobs.count{it.status=="expired"}.toString(),"Expired",Modifier.weight(1f))
                }
            }
        }
        item {
            ProCard {
                SectionHead(Icons.Default.Bolt,"VIP express publishing",
                    "Official careers link → reviewed draft → submit",Brand.violet)
                OutlinedTextField(link,{link=it},singleLine=true,
                    label={Text("Direct official job URL")},
                    leadingIcon={Icon(Icons.Default.Link,null)},
                    modifier=Modifier.fillMaxWidth(),shape=RoundedCornerShape(14.dp))
                Button(onClick={vm.extract(link)},enabled=!vm.busy&&link.startsWith("https://"),
                    modifier=Modifier.fillMaxWidth(),shape=RoundedCornerShape(13.dp)) {
                    Icon(Icons.Default.AutoAwesome,null)
                    Spacer(Modifier.width(8.dp))
                    Text("Generate draft")
                }
                vm.manualDraft?.let{draft->
                    HorizontalDivider(color=Brand.outline)
                    Row(verticalAlignment=Alignment.CenterVertically,
                        horizontalArrangement=Arrangement.spacedBy(10.dp)) {
                        CompanyMark(draft.optString("company"),vm.companyLogos,draft,43)
                        Text(draft.optString("company")+" — "+draft.optString("role"),
                        fontWeight=FontWeight.Bold,fontSize=13.sp,color=Brand.navy,
                            modifier=Modifier.weight(1f))
                    }
                    Text(draft.optString("desc").take(310),fontSize=12.sp,color=Brand.gray,
                        maxLines=6,overflow=TextOverflow.Ellipsis)
                    ProPill("Check all details before submitting",Brand.amber)
                    OutlinedButton(onClick={askPublish=true}) {Text("Review & submit VIP job")}
                }
            }
        }
        item {
            ProCard {
                SectionHead(Icons.Default.Search,"Published jobs",
                    "Search across your website listings")
                OutlinedTextField(query,{query=it},singleLine=true,
                    leadingIcon={Icon(Icons.Default.Search,null)},
                    label={Text("Company or job title")},modifier=Modifier.fillMaxWidth(),
                    shape=RoundedCornerShape(14.dp))
                Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                    listOf("All","Active","Expired").forEach{label->
                        FilterChip(selected=filter==label,onClick={filter=label},
                            label={Text(label,fontSize=11.sp)},shape=RoundedCornerShape(10.dp))
                    }
                }
                Text(filtered.size.toString()+" jobs found",fontSize=11.sp,color=Brand.gray)
            }
        }
        if(filtered.isEmpty())item{
            ProEmpty(Icons.Default.SearchOff,"No matching jobs","Try another search or status filter.")
        }
        items(filtered.take(120),key={it.id}) {job->
            ProCard {
                Row(verticalAlignment=Alignment.Top,horizontalArrangement=Arrangement.spacedBy(11.dp)){
                    CompanyMark(job.company,vm.companyLogos,job.raw,43)
                    Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(5.dp)) {
                        Text(job.company,fontSize=13.sp,fontWeight=FontWeight.Black,color=Brand.navy)
                        Text(job.role,fontSize=12.sp,fontWeight=FontWeight.SemiBold,color=Brand.navy,
                            lineHeight=18.sp)
                        Text(job.location,fontSize=11.sp,color=Brand.gray,maxLines=2)
                    }
                    ProPill(job.status.replaceFirstChar{it.uppercase()},
                        if(job.status=="active")Brand.green else Brand.amber)
                }
                if(job.apply.startsWith("https://"))TextButton(onClick={
                    ctx.startActivity(Intent(Intent.ACTION_VIEW,Uri.parse(job.apply)))
                }) {
                    Icon(Icons.Default.OpenInNew,null,Modifier.size(15.dp))
                    Spacer(Modifier.width(4.dp))
                    Text("View official application",fontSize=12.sp)
                }
            }
        }
    }
    if(askPublish)AlertDialog(onDismissRequest={askPublish=false},
        title={Text("Submit VIP job?",fontWeight=FontWeight.Black)},
        text={Text("Confirm that the extracted role, eligibility and direct application link are all correct. This sends a real publishing request.")},
        confirmButton={TextButton(onClick={askPublish=false;vm.publishManual()}){Text("Submit")}},
        dismissButton={TextButton(onClick={askPublish=false}){Text("Cancel")}})
}
