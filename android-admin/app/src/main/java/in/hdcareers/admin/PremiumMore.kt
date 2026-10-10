package `in`.hdcareers.admin

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlin.math.max

@Composable
internal fun ProMore(vm:AdminViewModel,onEnableBiometric:()->Unit,onNotifications:()->Unit) {
    var subpage by remember {mutableStateOf("")}
    val ctx=LocalContext.current
    when(subpage) {
        "analytics" -> ProAnalytics(vm,onBack={subpage=""})
        "checker" -> ProChecker(vm,onBack={subpage=""})
        else -> LazyColumn(contentPadding=PaddingValues(16.dp),
            verticalArrangement=Arrangement.spacedBy(14.dp)) {
            item {
                ProHero("Settings & intelligence","Your tools.\nYour control.",
                    "Analytics, automations, alerts and security in one place.",
                    icon=Icons.Default.Tune)
            }
            item {
                ProCard {
                    SectionHead(Icons.Default.Insights,"Insights & reports",
                        "Monitor growth and application activity",Brand.violet)
                    SettingRow(Icons.Default.QueryStats,"Detailed analytics",
                        "Traffic trends, visitor segments and conversions",Brand.blue) {
                        subpage="analytics"
                    }
                    HorizontalDivider(color=Brand.outline)
                    SettingRow(Icons.Default.Shield,"Expired job checker",
                        "Review suspicious listings with evidence",Brand.amber) {
                        subpage="checker"
                    }
                }
            }
            item {
                ProCard {
                    SectionHead(Icons.Default.Security,"Security & access",
                        "Protect your private publishing controls",Brand.green)
                    OutlinedButton(onClick=onEnableBiometric,modifier=Modifier.fillMaxWidth(),
                        shape=RoundedCornerShape(13.dp)) {
                        Icon(Icons.Default.Fingerprint,null,Modifier.size(18.dp))
                        Spacer(Modifier.width(9.dp))
                        Text("Enable fingerprint unlock")
                    }
                    TextButton(onClick={vm.logout()}) {
                        Icon(Icons.Default.Logout,null,Modifier.size(18.dp))
                        Spacer(Modifier.width(7.dp))
                        Text("Sign out & clear stored credentials")
                    }
                }
            }
            item {
                ProCard {
                    SectionHead(Icons.Default.Language,"HD Careers website","Manage in the browser too")
                    TextButton(onClick={ctx.startActivity(Intent(Intent.ACTION_VIEW,
                        Uri.parse("https://hdcareers.in/admin/")))}) {
                        Text("Open the web admin")
                        Icon(Icons.Default.OpenInNew,null,Modifier.size(16.dp))
                    }
                    Row(verticalAlignment=Alignment.CenterVertically,
                        horizontalArrangement=Arrangement.spacedBy(7.dp)) {
                        BrandLogo(29,false)
                        Text("HD Careers Admin · Private Android edition",color=Brand.gray,
                            fontSize=11.sp)
                    }
                }
            }
        }
    }
}
@Composable
private fun SettingRow(
    icon:androidx.compose.ui.graphics.vector.ImageVector,title:String,subtitle:String,
    color:Color,onClick:()->Unit
) {
    Row(Modifier.fillMaxWidth().clickable(onClick=onClick).padding(vertical=5.dp),
        verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(11.dp)) {
        Surface(color=color.copy(alpha=.09f),shape=RoundedCornerShape(12.dp)) {
            Box(Modifier.size(38.dp),contentAlignment=Alignment.Center) {
                Icon(icon,null,Modifier.size(20.dp),tint=color)
            }
        }
        Column(Modifier.weight(1f)) {
            Text(title,fontWeight=FontWeight.Bold,color=Brand.navy,fontSize=13.sp)
            Text(subtitle,fontSize=11.sp,color=Brand.gray,lineHeight=15.sp)
        }
        Icon(Icons.Default.ChevronRight,null,tint=Brand.gray)
    }
}
@Composable
private fun ProAnalytics(vm:AdminViewModel,onBack:()->Unit) {
    LazyColumn(contentPadding=PaddingValues(16.dp),
        verticalArrangement=Arrangement.spacedBy(14.dp)) {
        item {
            TextButton(onClick=onBack) {
                Icon(Icons.AutoMirrored.Filled.ArrowBack,null)
                Spacer(Modifier.width(7.dp))
                Text("Back to admin center")
            }
            ProHero("Google Analytics 4","Performance,\nbeautifully clear.",
                "See what visitors are doing across HD Careers.",
                icon=Icons.Default.Insights) {
                Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                    HeroMiniStat(vm.traffic.live.toString(),"Live now",Modifier.weight(1f))
                    HeroMiniStat(vm.traffic.users.toString(),"Visitors",Modifier.weight(1f))
                    HeroMiniStat(vm.traffic.views.toString(),"Views",Modifier.weight(1f))
                }
            }
        }
        item {
            ProCard {
                SectionHead(Icons.Default.CalendarMonth,"Reporting period",
                    "Change the timeframe to refresh all metrics")
                SingleChoiceSegmentedButtonRow(modifier=Modifier.fillMaxWidth()) {
                    listOf(1 to "24H",7 to "7D",30 to "30D").forEachIndexed { index,pair ->
                        SegmentedButton(
                            selected=vm.days==pair.first,onClick={vm.changeDays(pair.first)},
                            shape=SegmentedButtonDefaults.itemShape(index=index,count=3),
                            label={Text(pair.second,fontWeight=FontWeight.SemiBold)}
                        )
                    }
                }
            }
        }
        item {
            MetricsGrid(listOf(
                MetricSpec("Unique visitors",vm.traffic.users.toString(),Icons.Default.People,Brand.blue),
                MetricSpec("Page views",vm.traffic.views.toString(),Icons.Default.Visibility,Brand.violet),
                MetricSpec("Sessions",vm.traffic.sessions.toString(),Icons.Default.Timeline,Brand.cyan),
                MetricSpec("New visitors",vm.traffic.newUsers.toString(),Icons.Default.PersonAdd,Brand.green)
            ))
        }
        item {
            ProCard {
                SectionHead(Icons.Default.ShowChart,"Audience growth",
                    "Daily pageviews from Google Analytics",Brand.cyan)
                if(vm.traffic.trend.isNotEmpty()) {
                    TrendSpark(vm.traffic.trend,accent=Brand.blue)
                    Row(horizontalArrangement=Arrangement.SpaceBetween,
                        modifier=Modifier.fillMaxWidth()) {
                        Text(vm.traffic.trend.first().date,fontSize=10.sp,color=Brand.gray)
                        Text(vm.traffic.trend.last().date,fontSize=10.sp,color=Brand.gray)
                    }
                } else {
                    Text("GA4 has not returned trend data for this period.",
                        color=Brand.gray,fontSize=12.sp)
                }
                ProPill("Engagement "+String.format(java.util.Locale.US,"%.1f",vm.traffic.engagementRate)+"%",
                    Brand.green,Icons.Default.TrendingUp)
            }
        }
        item {
            ProCard {
                SectionHead(Icons.Default.AdsClick,"Conversions","Actions that turn visitors into applicants",
                    Brand.violet)
                Row(horizontalArrangement=Arrangement.spacedBy(10.dp)) {
                    ProMetric("Apply clicks",vm.traffic.applies.toString(),
                        Icons.Default.TouchApp,Brand.violet,Modifier.weight(1f))
                    ProMetric("Resume checks",vm.traffic.resumes.toString(),
                        Icons.Default.Description,Brand.cyan,Modifier.weight(1f))
                }
                ProPill("Apply conversion "+String.format(java.util.Locale.US,"%.1f",vm.traffic.applyRate)+"%",
                    Brand.blue)
            }
        }
        item {
            ProCard {
                SectionHead(Icons.Default.Devices,"Devices & platforms",
                    "Where your audience is browsing",Brand.violet)
                DonutDevices(vm.traffic.devices)
            }
        }
        item {
            ProCard {
                SectionHead(Icons.Default.Public,"Top countries","Where your visitors are",Brand.blue)
                val max=vm.traffic.countries.maxOfOrNull{it.second}?:1
                if(vm.traffic.countries.isEmpty()) EmptyReport()
                vm.traffic.countries.forEach {(name,value)->
                    ProBarRow(name,value,max)
                }
            }
        }
        item {
            ProCard {
                SectionHead(Icons.Default.Link,"Acquisition channels",
                    "How people discover HD Careers",Brand.cyan)
                val max=vm.traffic.channels.maxOfOrNull{it.second}?:1
                if(vm.traffic.channels.isEmpty()) EmptyReport()
                vm.traffic.channels.forEach {(name,value)->
                    ProBarRow(name,value,max,Brand.cyan)
                }
            }
        }
        item {
            ProCard {
                SectionHead(Icons.Default.Article,"Popular pages",
                    "Most viewed content on the website",Brand.amber)
                val max=vm.traffic.pages.maxOfOrNull{it.second}?:1
                if(vm.traffic.pages.isEmpty()) EmptyReport()
                vm.traffic.pages.forEach {(name,value)->
                    ProBarRow(name.replace("/jobs/","").replace("-"," ").take(58),
                        value,max,Brand.violet)
                }
            }
        }
        item {
            ProCard {
                SectionHead(Icons.Default.TravelExplore,"Traffic sources",
                    "Referrals and search discovery",Brand.blue)
                val max=vm.traffic.sources.maxOfOrNull{it.second}?:1
                if(vm.traffic.sources.isEmpty()) EmptyReport()
                vm.traffic.sources.forEach{(name,value)->
                    ProBarRow(name.ifBlank{"Direct / Unknown"},value,max,Brand.blue)
                }
                if(vm.traffic.updatedAt.isNotBlank())
                    Text("GA4 refreshed: "+vm.traffic.updatedAt.take(16).replace("T"," "),
                        fontSize=11.sp,color=Brand.gray)
            }
        }
    }
}
@Composable
private fun EmptyReport() {
    Text("No measurements available for this period.",fontSize=12.sp,color=Brand.gray)
}
@Composable
private fun ProChecker(vm:AdminViewModel,onBack:()->Unit) {
    val result=vm.checker.optJSONObject("results")
    val list=result?.optJSONArray("items")
    LazyColumn(contentPadding=PaddingValues(16.dp),
        verticalArrangement=Arrangement.spacedBy(13.dp)) {
        item {
            TextButton(onClick=onBack) {
                Icon(Icons.AutoMirrored.Filled.ArrowBack,null)
                Spacer(Modifier.width(7.dp)); Text("Back to admin center")
            }
            ProHero("Expiry management","Keep listings\ntrustworthy.",
                "Blockers and CAPTCHA do not prove jobs have expired.",
                icon=Icons.Default.Shield)
        }
        item {
            MetricsGrid(listOf(
                MetricSpec("Checked",(result?.optInt("checked")?:0).toString(),
                    Icons.Default.FactCheck,Brand.blue),
                MetricSpec("Needs review",(result?.optInt("review")?:0).toString(),
                    Icons.Default.WarningAmber,Brand.amber),
                MetricSpec("Active",(result?.optInt("active")?:0).toString(),
                    Icons.Default.CheckCircle,Brand.green),
                MetricSpec("Expired",(result?.optInt("expired")?:0).toString(),
                    Icons.Default.Cancel,Brand.red)
            ))
        }
        item {
            ProCard {
                SectionHead(Icons.Default.Shield,"Verification actions",
                    "Decisions are never based on HTTP blocking alone")
                Button(onClick=vm::checkerRun,enabled=!vm.busy,modifier=Modifier.fillMaxWidth(),
                    shape=RoundedCornerShape(14.dp)) {
                    Icon(Icons.Default.Refresh,null)
                    Spacer(Modifier.width(8.dp))
                    Text("Run expired-job checker")
                }
            }
        }
        if(list!=null)items(list.length()) {index->
            val j=list.optJSONObject(index)
            if(j!=null&&j.optString("state")=="review") {
                ProCard {
                    SectionHead(Icons.Default.WarningAmber,
                        j.optString("company","Unknown employer"),j.optString("role"),Brand.amber)
                    Text(j.optString("reason"),fontSize=12.sp,color=Brand.gray,lineHeight=18.sp)
                    val jobId=j.optInt("id",-1)
                    Row(horizontalArrangement=Arrangement.spacedBy(10.dp)) {
                        OutlinedButton(onClick={vm.checkerResolve(jobId,"keep")},
                            enabled=jobId>=0&&!vm.busy,modifier=Modifier.weight(1f)) {
                            Text("Keep live",fontSize=11.sp)
                        }
                        OutlinedButton(onClick={vm.checkerResolve(jobId,"expire")},
                            enabled=jobId>=0&&!vm.busy,modifier=Modifier.weight(1f)) {
                            Text("Expire job",fontSize=11.sp)
                        }
                    }
                }
            }
        }
    }
}