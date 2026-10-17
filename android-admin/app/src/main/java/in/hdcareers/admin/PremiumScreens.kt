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
    MaterialTheme(colorScheme=Brand.scheme,typography=Typography()) {
        if(!vm.loggedIn) {
            ProLogin(vm,onBiometricSignIn)
        } else {
            Scaffold(
                containerColor=Brand.background,
                topBar={
                    Surface(modifier=Modifier.fillMaxWidth().statusBarsPadding(),
                        color=Color.White,shadowElevation=1.dp) {
                        Row(Modifier.fillMaxWidth().padding(horizontal=16.dp,vertical=12.dp),
                            verticalAlignment=Alignment.CenterVertically,
                            horizontalArrangement=Arrangement.spacedBy(12.dp)) {
                            BrandLogo(39,false)
                            Column(Modifier.weight(1f)) {
                                Text("HD CAREERS",fontSize=10.sp,fontWeight=FontWeight.Black,
                                    letterSpacing=1.1.sp,color=Brand.blue)
                                Text(if(moreOpen)"Settings" else listOf("Today","Publish","Expiry","Jobs","Analytics")[vm.tab.coerceIn(0,4)],
                                    fontSize=19.sp,fontWeight=FontWeight.Black,color=Brand.navy)
                            }
                            BadgedBox(badge={if(vm.batch.id.isNotBlank()&&vm.batch.reviewed<vm.batch.all.size)
                                Badge(containerColor=Brand.amber){} }) {
                                IconButton(onClick={moreOpen=false;vm.tab=1}) {
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
                },
                bottomBar={
                    NavigationBar(containerColor=Color.White,tonalElevation=4.dp) {
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
                    if(moreOpen) ProMore(vm,onEnableBiometric,onRequestNotificationPermission) else when(vm.tab) {
                        0 -> ProHome(vm,onAnalytics={vm.tab=4})
                        1 -> ProReview(vm)
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
    val awaiting=vm.batch.priority.count{it.decision!="live"}
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
                    HeroMiniStat(awaiting.toString(),"To review",Modifier.weight(1f))
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
                    QuickAction("Jobs",Icons.Default.BusinessCenter,Brand.violet,Modifier.weight(1f)){vm.tab=2}
                    if(vm.adminRole=="owner") QuickAction("Analytics",Icons.Default.Insights,Brand.cyan,Modifier.weight(1f)){onAnalytics()}
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
private fun ProReview(vm:AdminViewModel) {
    var selected by remember { mutableIntStateOf(0) }
    var confirm by remember { mutableStateOf(false) }
    val chosen=vm.batch.all.filter { it.id in vm.selectedIds }
    val raw=when(selected) {
        0 -> vm.batch.priority.filterNot { it.id in vm.selectedIds }
        1 -> vm.batch.backup.filterNot { it.id in vm.selectedIds }
        else -> chosen
    }
    val candidates=if(selected==2)raw else raw.sortedWith(compareBy<Candidate> {
        when(it.decision) { "live" -> 0; "unreviewed", "" -> 1; "unsure" -> 2; else -> 3 }
    }.thenByDescending { it.complete })
    val total=vm.batch.all.size
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
                if(swipe < -80f) selected=(selected+1).coerceAtMost(2)
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
                Text("20 employers: ${vm.batch.uniqueEmployers}/20 · Source details required: ${vm.batch.incomplete}",
                    fontSize=12.sp,color=Brand.gray)
                TabRow(selectedTabIndex=selected,containerColor=Color.Transparent,
                    contentColor=Brand.blue) {
                    listOf("Priority","Backup","Publish Ready").forEachIndexed {index,label->
                        Tab(selected=selected==index,onClick={selected=index},
                            text={Text(if(index==2)"Ready (${chosen.size})" else label,
                                fontWeight=FontWeight.Bold,fontSize=11.sp,maxLines=1)})
                    }
                }
                Text(when(selected){
                    0 -> "Priority: source-checked roles first. Expired roles remain visible for audit."
                    1 -> "Backup: Live roles here can also go directly to Publish Ready."
                    else -> "Final review: only complete, verified jobs can be published."
                },fontSize=11.sp,color=Brand.gray)
            }
        }
        item {
            ProCard {
                SectionHead(Icons.Default.NotificationsActive,"Two-job test inbox","Separate from your submitted daily batch")
                Text("Test drafts and Firebase push. Production publishing is disabled for these test drafts until the independent backend receipt tracker is complete.",
                    fontSize=12.sp,color=Brand.gray,lineHeight=18.sp)
                val inbox=vm.twoJobInbox.optJSONObject("staged")
                val entries=inbox?.optJSONArray("jobs")
                if(entries==null) {
                    Text("No test inbox loaded",fontSize=12.sp,color=Brand.amber)
                } else {
                    Text("Staged jobs: ${entries.length()} · Review only",fontSize=12.sp,color=Brand.green)
                    for(n in 0 until entries.length()){
                        val j=entries.optJSONObject(n) ?: continue
                        HorizontalDivider()
                        Text(j.optString("company")+" · "+j.optString("role"),fontWeight=FontWeight.Bold,fontSize=13.sp)
                        Text("Status: Awaiting individual review · Not submitted to publisher",fontSize=11.sp,color=Brand.gray)
                        val uri=j.optString("apply")
                        val ctx=LocalContext.current
                        TextButton(onClick={if(uri.startsWith("https://"))ctx.startActivity(Intent(Intent.ACTION_VIEW,Uri.parse(uri)))}) { Text("Open official application") }
                    }
                }
                Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick=vm::loadTwoJobInbox,enabled=!vm.busy) { Text("Refresh test jobs") }
                    Button(onClick=vm::stageTwoJobInbox,enabled=!vm.busy && entries==null) { Text("Stage 2 test jobs") }
                }
                Text("No demo success is presented as real deployment. Per-job GitHub, website and Telegram receipts remain pending backend integration.",
                    fontSize=11.sp,color=Brand.gray)
            }
        }
        if(vm.batch.id.isBlank()) item {
            ProEmpty(Icons.Default.EventNote,"No batch available",
                "The discovery pipeline must generate real source-backed jobs first.",
                "Refresh now",vm::refreshClicked)
        } else if(candidates.isEmpty()) item {
            ProEmpty(Icons.Default.CheckCircle,
                if(selected==2)"Nothing in Publish Ready" else "No jobs remaining in this section",
                if(selected==2)"Verify a role Live and tap Add to Publish Ready in Priority or Backup."
                else "Selected jobs have moved to Publish Ready.",
                "Refresh",vm::refreshClicked)
        }
        itemsIndexed(candidates,key={_,item->item.id}) {i,job->
            ProCandidateCard(job,i,selected==0,vm.companyLogos,vm.busy,
                chosen=job.id in vm.selectedIds,published=job.id in vm.publishedReviewIds,
                inReady=selected==2,decide={vm.decide(job.id,it)},
                 verifyAndAdd={vm.verifyAndAdd(job.id)},
                toggle={vm.toggleSelected(job.id,it)})
        }
        if(vm.batch.id.isNotBlank() && selected==2) item {
            ProCard {
                SectionHead(Icons.Default.RocketLaunch,"Publish Ready",
                    "Review your selected jobs before final confirmation",Brand.green)
                val incomplete=chosen.filterNot { it.approved }
                Text("${chosen.size} of 10 selected · ${incomplete.size} awaiting source details",
                    color=if(incomplete.isEmpty())Brand.green else Brand.amber,fontSize=12.sp)
                if(incomplete.isNotEmpty()) {
                    Text("Incomplete information must be recovered from the official job page. We won't invent eligibility, responsibilities or experience requirements.",
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
                Text("Website deployment first. New jobs then enter the hourly Telegram queue.",
                    fontSize=11.sp,color=Brand.gray)
                OutlinedButton(onClick=vm::refreshPublishingStatus,enabled=!vm.busy,
                    modifier=Modifier.fillMaxWidth()) { Text("Refresh live publishing status") }
                val progress=vm.publishingProgress
                val gh=progress.optJSONObject("workflow")
                Text("GitHub: "+(gh?.optString("conclusion")?.takeIf { it.isNotBlank() }
                    ?:gh?.optString("state").orEmpty().ifBlank { "Not submitted" }),
                    fontSize=12.sp,color=Brand.navy)
                Text("Website Live: ${progress.optInt("publishedCount")} · Telegram queued: ${progress.optInt("telegramHourlyPending")} · Delivered: ${progress.optInt("telegramDelivered")}",
                    fontSize=12.sp,color=Brand.navy)
                Text("Live tracking refreshes every 10 seconds after submission; a commit alone is not a delivery.",
                    fontSize=11.sp,color=Brand.gray)
                val stages=progress.optJSONArray("stages")
                for(i in 0 until (stages?.length() ?: 0)) {
                    val stage=stages?.optJSONObject(i) ?: continue
                    Text(stage.optString("company")+
                        " · GitHub "+stage.optString("github")+
                        " · Site "+stage.optString("website")+
                        " · Telegram "+stage.optString("telegram"),
                        fontSize=11.sp,color=Brand.gray)
                }
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
private fun ProCandidateCard(c:Candidate,index:Int,priority:Boolean,
    logos:Map<String,CompanyLogoSource>,busy:Boolean,
    chosen:Boolean,published:Boolean,inReady:Boolean,
    decide:(String)->Unit,verifyAndAdd:()->Unit,toggle:(Boolean)->Unit) {
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
