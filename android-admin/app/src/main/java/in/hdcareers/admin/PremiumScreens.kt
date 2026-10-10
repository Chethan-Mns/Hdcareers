package `in`.hdcareers.admin

import android.content.Intent
import android.net.Uri
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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

@Composable
fun PremiumAdminRoot(
    vm:AdminViewModel,
    onBiometricSignIn:()->Unit,
    onEnableBiometric:()->Unit,
    onRequestNotificationPermission:()->Unit
) {
    MaterialTheme(colorScheme=Brand.scheme,typography=Typography()) {
        if(!vm.loggedIn) {
            ProLogin(vm,onBiometricSignIn)
        } else {
            Scaffold(
                containerColor=Brand.background,
                topBar={
                    Surface(color=Color.White,shadowElevation=1.dp) {
                        Row(Modifier.fillMaxWidth().padding(horizontal=16.dp,vertical=12.dp),
                            verticalAlignment=Alignment.CenterVertically,
                            horizontalArrangement=Arrangement.spacedBy(12.dp)) {
                            BrandLogo(39,false)
                            Column(Modifier.weight(1f)) {
                                Text("HD CAREERS",fontSize=10.sp,fontWeight=FontWeight.Black,
                                    letterSpacing=1.1.sp,color=Brand.blue)
                                Text(listOf("Overview","Daily Review","Job Manager","Admin Center")[vm.tab],
                                    fontSize=19.sp,fontWeight=FontWeight.Black,color=Brand.navy)
                            }
                            BadgedBox(badge={if(vm.batch.id.isNotBlank()&&vm.batch.reviewed<20)
                                Badge(containerColor=Brand.amber){} }) {
                                IconButton(onClick={vm.tab=1}) {
                                    Icon(Icons.Default.NotificationsNone,"Review notifications",tint=Brand.navy)
                                }
                            }
                            IconButton(onClick={vm::refreshClicked}) {
                                Icon(Icons.Default.Refresh,"Refresh server data",tint=Brand.blue)
                            }
                        }
                    }
                },
                bottomBar={
                    NavigationBar(containerColor=Color.White,tonalElevation=4.dp) {
                        val labels=listOf("Home","Review","Jobs","More")
                        val symbols=listOf(Icons.Default.Dashboard,Icons.Default.FactCheck,
                            Icons.Default.BusinessCenter,Icons.Default.GridView)
                        labels.forEachIndexed { index,label ->
                            NavigationBarItem(selected=vm.tab==index,onClick={vm.tab=index},
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
                    when(vm.tab) {
                        0 -> ProHome(vm)
                        1 -> ProReview(vm)
                        2 -> ProJobs(vm)
                        else -> ProMore(vm,onEnableBiometric,onRequestNotificationPermission)
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
    Box(Modifier.fillMaxSize().background(Brand.background)) {
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
private fun ProHome(vm:AdminViewModel) {
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
            MetricsGrid(listOf(
                MetricSpec("Published jobs",vm.jobs.size.toString(),Icons.Default.Work,Brand.blue),
                MetricSpec("Active listings",active.toString(),Icons.Default.CheckCircle,Brand.green),
                MetricSpec("Page views",vm.traffic.views.toString(),Icons.Default.Visibility,Brand.violet),
                MetricSpec("Apply clicks",vm.traffic.applies.toString(),Icons.Default.TouchApp,Brand.cyan)
            ))
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
                SectionHead(Icons.Default.ShowChart,"Traffic trend",
                    "Real Google Analytics data · "+vm.days+" day view",Brand.cyan,
                    action={vm.tab=3})
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
                    QuickAction("Analytics",Icons.Default.Insights,Brand.cyan,Modifier.weight(1f)){vm.tab=3}
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
    var selected by remember {mutableIntStateOf(0)}
    var confirm by remember {mutableStateOf(false)}
    val candidates=if(selected==0)vm.batch.priority else vm.batch.backup
    val total=vm.batch.priority.size+vm.batch.backup.size
    LazyColumn(contentPadding=PaddingValues(16.dp),
        verticalArrangement=Arrangement.spacedBy(13.dp)) {
        item {
            ProHero("Daily publishing","Your 20-job\nreview desk.",
                "Verify the Top 10, keep ten backups, and publish only when ready.",
                icon=Icons.Default.FactCheck) {
                Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                    HeroMiniStat(vm.batch.priority.size.toString(),"Priority",Modifier.weight(1f))
                    HeroMiniStat(vm.batch.backup.size.toString(),"Backups",Modifier.weight(1f))
                    HeroMiniStat(vm.batch.reviewed.toString(),"Reviewed",Modifier.weight(1f))
                }
            }
        }
        item {
            ProCard {
                SectionHead(Icons.Default.FactCheck,"Review queue","Manual verification is required")
                LinearProgressIndicator(progress={vm.batch.reviewed.toFloat()/max(1,total)},
                    modifier=Modifier.fillMaxWidth().height(7.dp).clip(RoundedCornerShape(8.dp)),
                    color=Brand.blue,trackColor=Brand.sky)
                TabRow(selectedTabIndex=selected,containerColor=Color.Transparent,
                    contentColor=Brand.blue) {
                    listOf("Priority 10","Backup 10").forEachIndexed {index,name->
                        Tab(selected=selected==index,onClick={selected=index},
                            text={Text(name,fontWeight=FontWeight.Bold,fontSize=12.sp)})
                    }
                }
            }
        }
        if(vm.batch.id.isBlank()) item {
            ProEmpty(Icons.Default.EventNote,"No batch available",
                "When the discovery pipeline prepares 10 priority and 10 backup jobs, they'll appear here. No example jobs are shown as live.",
                "Refresh now",vm::refreshClicked)
        }
        itemsIndexed(candidates,key={_,item->item.id}) {i,job->
            ProCandidateCard(job,i,selected==0,vm.batch.backup,vm.busy,
                decide={vm.decide(job.id,it)},replace={vm.swap(job.id,it)})
        }
        if(selected==0&&vm.batch.id.isNotBlank()) item {
            ProCard {
                SectionHead(Icons.Default.RocketLaunch,"Publish approved batch",
                    "Ten jobs, ten distinct employers",Brand.green)
                Text("Publishing requires 8 fresher IT, 1 non-IT and 1 internship/apprenticeship, all confirmed Live and fully documented.",
                    fontSize=12.sp,color=Brand.gray,lineHeight=18.sp)
                Button(onClick={confirm=true},enabled=vm.batch.ready&&!vm.busy,
                    modifier=Modifier.fillMaxWidth(),shape=RoundedCornerShape(14.dp)) {
                    Icon(Icons.Default.Send,null)
                    Spacer(Modifier.width(8.dp))
                    Text("Approve and publish selected jobs")
                }
                ProPill(if(vm.batch.ready)"Ready for your approval" else "Review and content checks pending",
                    if(vm.batch.ready)Brand.green else Brand.amber)
                Text("Website deployment and Telegram delivery are tracked separately.",
                    color=Brand.gray,fontSize=11.sp)
            }
        }
    }
    if(confirm) AlertDialog(onDismissRequest={confirm=false},
        title={Text("Publish 10 verified jobs?",fontWeight=FontWeight.Black)},
        text={Text("This sends your reviewed jobs to the existing publishing pipeline. The app will not claim Telegram delivery until separately confirmed.")},
        confirmButton={TextButton(onClick={confirm=false;vm.publishBatch()}){Text("Publish jobs")}},
        dismissButton={TextButton(onClick={confirm=false}){Text("Cancel")}})
}

@Composable
private fun ProCandidateCard(c:Candidate,index:Int,priority:Boolean,
    backups:List<Candidate>,busy:Boolean,decide:(String)->Unit,replace:(String)->Unit) {
    var expanded by remember {mutableStateOf(false)}
    val ctx=LocalContext.current
    val replacements=backups.filter{it.group==c.group&&it.decision=="live"&&it.company!=c.company}
    val category=when(c.group) {"nonit"->"Non-IT";"training"->"Internship / Apprentice";else->"Fresher IT"}
    val decisionColor=when(c.decision) {
        "live"->Brand.green;"expired"->Brand.red;"unsure"->Brand.amber;else->Brand.blue
    }
    ProCard {
        Row(verticalAlignment=Alignment.Top,horizontalArrangement=Arrangement.spacedBy(12.dp)) {
            Box(Modifier.size(45.dp).clip(RoundedCornerShape(13.dp))
                .background(Brand.sky),contentAlignment=Alignment.Center) {
                Text(c.company.take(2).uppercase(),fontSize=15.sp,fontWeight=FontWeight.Black,color=Brand.blue)
            }
            Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(3.dp)) {
                Text(c.company,fontWeight=FontWeight.ExtraBold,color=Brand.navy,fontSize=14.sp)
                Text(c.role,fontWeight=FontWeight.Bold,color=Brand.navy,fontSize=13.sp,
                    lineHeight=18.sp)
                Text(listOf(c.location,c.experience).filter{it.isNotBlank()}.joinToString(" · "),
                    fontSize=11.sp,color=Brand.gray)
            }
            Text("#"+(index+1),color=Brand.gray,fontSize=11.sp,fontWeight=FontWeight.Bold)
        }
        Row(horizontalArrangement=Arrangement.spacedBy(7.dp)) {
            ProPill(category,Brand.blue)
            ProPill(c.decision.ifBlank{"Needs review"}.replaceFirstChar{it.uppercase()},
                decisionColor)
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
                val checked=status==c.decision
                OutlinedButton(onClick={decide(status)},enabled=!busy,
                    shape=RoundedCornerShape(11.dp),contentPadding=PaddingValues(horizontal=8.dp),
                    modifier=Modifier.weight(1f).height(37.dp),
                    colors=ButtonDefaults.outlinedButtonColors(
                        containerColor=if(checked)color.copy(alpha=.10f) else Color.White),
                    border=androidx.compose.foundation.BorderStroke(1.dp,
                        if(checked) color.copy(alpha=.5f) else Brand.outline)) {
                    Text(status.replaceFirstChar{it.uppercase()},fontWeight=FontWeight.Bold,
                        fontSize=10.sp,color=color,maxLines=1)
                }
            }
        }
        if(priority) Box {
            OutlinedButton(onClick={expanded=true},enabled=replacements.isNotEmpty()&&!busy,
                shape=RoundedCornerShape(12.dp),modifier=Modifier.fillMaxWidth()) {
                Icon(Icons.Default.SwapHoriz,null,Modifier.size(18.dp))
                Spacer(Modifier.width(7.dp))
                Text("Replace from verified backups",fontSize=12.sp)
            }
            DropdownMenu(expanded=expanded,onDismissRequest={expanded=false}) {
                replacements.forEach {candidate->
                    DropdownMenuItem(text={Text(candidate.company+" — "+candidate.role,
                        fontSize=12.sp,maxLines=2)},
                        onClick={expanded=false;replace(candidate.id)})
                }
            }
        }
        if(!c.complete) Text("Full verified description is still required before publishing.",
            fontSize=11.sp,color=Brand.amber)
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
                    Text(draft.optString("company")+" — "+draft.optString("role"),
                        fontWeight=FontWeight.Bold,fontSize=13.sp,color=Brand.navy)
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
                    Box(Modifier.size(43.dp).clip(RoundedCornerShape(12.dp)).background(Brand.sky),
                        contentAlignment=Alignment.Center) {
                        Text(job.company.take(2).uppercase(),fontWeight=FontWeight.Black,color=Brand.blue)
                    }
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
