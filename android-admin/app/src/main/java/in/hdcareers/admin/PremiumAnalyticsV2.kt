package `in`.hdcareers.admin

import androidx.compose.animation.core.*
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlin.math.max
import java.util.Locale

@Composable
internal fun ProAnalyticsV2(vm:AdminViewModel) {
    var metric by remember { mutableStateOf("Views") }
    val data=vm.traffic
    val trend=if(metric=="Visitors") data.trend.map{it.copy(views=it.visitors)} else data.trend
    LazyColumn(contentPadding=PaddingValues(start=16.dp,end=16.dp,top=17.dp,bottom=36.dp),
        verticalArrangement=Arrangement.spacedBy(14.dp)) {
        item {
            ProHero("REALTIME GA4 INSIGHTS","Your audience.\nIn motion.",
                "Animated, source-backed analytics for every published opportunity.",
                icon=Icons.Default.Insights) {
                Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                    HeroMiniStat(data.live.toString(),"Live now",Modifier.weight(1f))
                    HeroMiniStat(data.users.toString(),"Visitors",Modifier.weight(1f))
                    HeroMiniStat(data.applies.toString(),"Apply clicks",Modifier.weight(1f))
                }
            }
        }
        item {
            ProCard {
                SectionHead(Icons.Default.CalendarMonth,"Reporting window",
                    "Refresh every metric for the selected period")
                SingleChoiceSegmentedButtonRow(Modifier.fillMaxWidth()) {
                    listOf(1 to "24H",7 to "7D",30 to "30D").forEachIndexed{index,pair->
                        SegmentedButton(selected=vm.days==pair.first,
                            onClick={vm.changeDays(pair.first)},
                            shape=SegmentedButtonDefaults.itemShape(index=index,count=3),
                            label={Text(pair.second,fontWeight=FontWeight.Bold)})
                    }
                }
            }
        }
        item {
            MetricsGrid(listOf(
                MetricSpec("Page views",data.views.toString(),Icons.Default.Visibility,Brand.violet),
                MetricSpec("Sessions",data.sessions.toString(),Icons.Default.Analytics,Brand.blue),
                MetricSpec("New visitors",data.newUsers.toString(),Icons.Default.PersonAdd,Brand.green),
                MetricSpec("Resume checks",data.resumes.toString(),Icons.Default.Description,Brand.amber)
            ))
        }
        item {
            ProCard {
                SectionHead(Icons.Default.AutoGraph,"Audience growth",
                    "Interactive views and visitors over time",Brand.cyan)
                SingleChoiceSegmentedButtonRow(Modifier.fillMaxWidth()) {
                    listOf("Views","Visitors").forEachIndexed {i,key->
                        SegmentedButton(selected=metric==key,onClick={metric=key},
                            shape=SegmentedButtonDefaults.itemShape(index=i,count=2),
                            label={Text(key)})
                    }
                }
                if(trend.isNotEmpty()) {
                    TrendSpark(trend,accent=if(metric=="Views")Brand.violet else Brand.cyan)
                    Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) {
                        Text(trend.first().date,fontSize=10.sp,color=Brand.gray)
                        Text(trend.last().date,fontSize=10.sp,color=Brand.gray)
                    }
                }else Text("GA4 has no trend measurements for this window.",fontSize=12.sp,color=Brand.gray)
                ProPill("Engagement "+String.format(Locale.US,"%.1f",data.engagementRate)+"%",
                    Brand.green,Icons.Default.TrendingUp)
            }
        }
        item {
            ProCard {
                SectionHead(Icons.Default.BubbleChart,"Audience constellation",
                    "Animated traffic sources instead of another bar chart",Brand.violet)
                AudienceConstellation(data.channels)
                Text("Bubble size represents session share.",fontSize=11.sp,color=Brand.gray)
            }
        }
        item {
            ProCard {
                SectionHead(Icons.Default.AdsClick,"Application conversions",
                    "Clicks are measured; applications submitted are not",Brand.blue)
                Row(horizontalArrangement=Arrangement.spacedBy(9.dp)) {
                    ProMetric("Apply clicks",data.applies.toString(),
                        Icons.Default.TouchApp,Brand.violet,Modifier.weight(1f))
                    ProMetric("Apply CTR",String.format(Locale.US,"%.1f%%",data.applyRate),
                        Icons.Default.TrendingUp,Brand.green,Modifier.weight(1f))
                }
            }
        }
        item {
            ProCard {
                SectionHead(Icons.Default.Devices,"Device ecosystem",
                    "Mobile versus desktop share",Brand.cyan)
                DonutDevices(data.devices)
            }
        }
        item {
            ProCard {
                SectionHead(Icons.Default.Public,"Where visitors connect",
                    "Geographic audience distribution",Brand.green)
                DonutDevices(data.countries.take(5))
            }
        }
        item {
            ProCard {
                SectionHead(Icons.Default.Article,"Most visited job pages",
                    "Real page views ranked by audience interest",Brand.violet)
                if(data.pages.isEmpty())Text("No job-page metrics available.",fontSize=12.sp,color=Brand.gray)
                else data.pages.take(6).forEachIndexed {i,entry->
                    Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically,
                        horizontalArrangement=Arrangement.spacedBy(9.dp)) {
                        Text((i+1).toString().padStart(2,'0'),color=Brand.violet,
                            fontWeight=FontWeight.Black,fontSize=14.sp)
                        Text(entry.first.removePrefix("/jobs/").replace('-',' ').take(45),
                            modifier=Modifier.weight(1f),fontSize=11.sp,color=Brand.navy)
                        Text(entry.second.toString(),fontWeight=FontWeight.Black,
                            fontSize=11.sp,color=Brand.navy)
                    }
                }
            }
        }
        item {
            ProCard {
                SectionHead(Icons.Default.Link,"Referrers","Search, social and direct channels",Brand.blue)
                if(data.sources.isEmpty())Text("No sources available.",fontSize=12.sp,color=Brand.gray)
                data.sources.take(5).forEach{(name,value)->
                    Row(Modifier.fillMaxWidth()) {
                        Text(name.ifBlank{"Direct"},modifier=Modifier.weight(1f),fontSize=12.sp,color=Brand.navy)
                        Text(value.toString(),fontWeight=FontWeight.Bold,color=Brand.blue,fontSize=12.sp)
                    }
                }
                Text("Last GA4 refresh: "+data.updatedAt.take(19).replace("T"," "),
                    fontSize=10.sp,color=Brand.gray)
            }
        }
    }
}

@Composable
private fun AudienceConstellation(items:List<Pair<String,Int>>) {
    val ranked=items.take(5)
    val total=ranked.sumOf {max(0,it.second)}.coerceAtLeast(1)
    val palette=listOf(Brand.blue,Brand.violet,Brand.cyan,Brand.green,Brand.amber)
    val motion=rememberInfiniteTransition(label="traffic orbit")
    val pulse by motion.animateFloat(.92f,1.08f,
        animationSpec=infiniteRepeatable(tween(1700,easing=FastOutSlowInEasing),
            repeatMode=RepeatMode.Reverse),label="orbit size")
    val points=listOf(.48f to .48f,.18f to .32f,.78f to .28f,.25f to .79f,.79f to .80f)
    Canvas(Modifier.fillMaxWidth().height(190.dp)) {
        ranked.forEachIndexed {i,p->
            val center=Offset(size.width*points[i].first,size.height*points[i].second)
            val r=(14.dp.toPx()+size.minDimension*.15f*(max(0,p.second).toFloat()/total))*pulse
            drawCircle(palette[i].copy(alpha=.14f),r*1.35f,center)
            drawCircle(Brush.radialGradient(listOf(palette[i],palette[i].copy(alpha=.46f))),r,center)
        }
        if(ranked.isEmpty())drawCircle(Brand.sky,size.minDimension*.19f,center)
    }
    if(ranked.isEmpty())Text("No traffic-source data yet.",fontSize=12.sp,color=Brand.gray)
    ranked.forEachIndexed {i,p->
        Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically) {
            Box(Modifier.size(9.dp).background(palette[i],CircleShape))
            Spacer(Modifier.width(9.dp))
            Text(p.first,modifier=Modifier.weight(1f),fontSize=11.sp,color=Brand.navy)
            Text((p.second*100/total).toString()+"%",color=palette[i],
                fontSize=11.sp,fontWeight=FontWeight.Black)
        }
    }
}
