package \`in\`.hdcareers.admin

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlin.math.max

internal object Brand {
    val navy=Color(0xFF071A33)
    val blue=Color(0xFF0969DA)
    val background=Color(0xFFF6F9FD)
    val sky=Color(0xFFECF4FF)
    val cyan=Color(0xFF059EC7)
    val green=Color(0xFF16A34A)
    val amber=Color(0xFFF49E09)
    val red=Color(0xFFDC2626)
    val violet=Color(0xFF6B3DE0)
    val gray=Color(0xFF708299)
    val outline=Color(0xFFE4EBF4)
    val surface=Color.White
    val darkBlue=Color(0xFF0B3F82)
    val scheme=lightColorScheme(
        primary=blue, secondary=cyan, background=background, surface=surface,
        onSurface=navy, onBackground=navy, outline=outline, error=red
    )
}
internal val hdCorners = RoundedCornerShape(20.dp)

@Composable
internal fun BrandLogo(size:Int=46, elevated:Boolean=true) {
    Box(
        modifier=Modifier.size(size.dp)
            .then(if(elevated)Modifier.shadow(5.dp,RoundedCornerShape(12.dp)) else Modifier)
            .background(Color.White,RoundedCornerShape(12.dp))
            .border(1.dp,Brand.outline,RoundedCornerShape(12.dp))
            .padding(4.dp),
        contentAlignment=Alignment.Center
    ) {
        Icon(painterResource(R.drawable.hd_careers_logo),contentDescription="HD Careers official logo",
            modifier=Modifier.fillMaxSize(),tint=Color.Unspecified)
    }
}

@Composable
internal fun ProCard(
    modifier:Modifier=Modifier, padding:Int=17,
    content:@Composable ColumnScope.()->Unit
) {
    Surface(
        modifier=modifier.shadow(9.dp,hdCorners,ambientColor=Brand.navy.copy(alpha=.08f),
            spotColor=Brand.navy.copy(alpha=.04f)),
        shape=hdCorners,color=Brand.surface,tonalElevation=0.dp,
        border=androidx.compose.foundation.BorderStroke(1.dp,Brand.outline.copy(alpha=.9f))
    ) {
        Column(Modifier.padding(padding.dp),verticalArrangement=Arrangement.spacedBy(10.dp),content=content)
    }
}
@Composable
internal fun SectionHead(icon:ImageVector,title:String,subtitle:String?=null,
                          accent:Color=Brand.blue,action:(()->Unit)?=null) {
    Row(verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(11.dp)) {
        Box(Modifier.size(36.dp).clip(RoundedCornerShape(11.dp))
            .background(accent.copy(alpha=.10f)),contentAlignment=Alignment.Center) {
            Icon(icon,null,Modifier.size(19.dp),tint=accent)
        }
        Column(Modifier.weight(1f)) {
            Text(title,fontWeight=FontWeight.ExtraBold,fontSize=15.sp,color=Brand.navy)
            if(subtitle!=null)Text(subtitle,fontSize=11.sp,color=Brand.gray,lineHeight=16.sp)
        }
        if(action!=null) IconButton(onClick=action,modifier=Modifier.size(32.dp)) {
            Icon(Icons.Default.ChevronRight,"Open",tint=Brand.gray)
        }
    }
}
@Composable
internal fun ProPill(label:String,color:Color=Brand.blue,icon:ImageVector?=null) {
    Row(
        modifier=Modifier.clip(CircleShape).background(color.copy(alpha=.095f))
            .padding(horizontal=10.dp,vertical=7.dp),
        horizontalArrangement=Arrangement.spacedBy(4.dp),
        verticalAlignment=Alignment.CenterVertically
    ) {
        if(icon!=null)Icon(icon,null,Modifier.size(13.dp),tint=color)
        Text(label,fontWeight=FontWeight.Bold,fontSize=10.sp,color=color,maxLines=1)
    }
}
@Composable
internal fun ProMetric(label:String,value:String,icon:ImageVector,accent:Color=Brand.blue,
                       modifier:Modifier=Modifier,caption:String?=null) {
    ProCard(modifier=modifier,padding=13) {
        Row(verticalAlignment=Alignment.CenterVertically) {
            Box(Modifier.size(33.dp).clip(RoundedCornerShape(10.dp))
                .background(accent.copy(alpha=.09f)),contentAlignment=Alignment.Center) {
                Icon(icon,null,Modifier.size(17.dp),tint=accent)
            }
            Spacer(Modifier.weight(1f))
            if(caption!=null)Text(caption,fontSize=10.sp,fontWeight=FontWeight.SemiBold,color=accent)
        }
        Text(value,fontSize=25.sp,fontWeight=FontWeight.Black,color=Brand.navy,
            lineHeight=28.sp,maxLines=1)
        Text(label,fontSize=11.sp,fontWeight=FontWeight.SemiBold,color=Brand.gray,
            maxLines=2,lineHeight=14.sp)
    }
}
@Composable
internal fun MetricsGrid(items:List<MetricSpec>) {
    Column(verticalArrangement=Arrangement.spacedBy(10.dp)) {
        items.chunked(2).forEach { chunk ->
            Row(horizontalArrangement=Arrangement.spacedBy(10.dp),modifier=Modifier.fillMaxWidth()) {
                for(item in chunk) ProMetric(item.label,item.value,item.icon,item.color,Modifier.weight(1f),item.caption)
                if(chunk.size<2)Spacer(Modifier.weight(1f))
            }
        }
    }
}
internal data class MetricSpec(val label:String,val value:String,val icon:ImageVector,
                               val color:Color=Brand.blue,val caption:String?=null)

@Composable
internal fun ProHero(eyebrow:String,headline:String,detail:String,modifier:Modifier=Modifier,
                     icon:ImageVector=Icons.Default.AutoAwesome,
                     children:@Composable ColumnScope.()->Unit = {}) {
    Box(modifier=modifier.fillMaxWidth().shadow(15.dp,RoundedCornerShape(25.dp),
        ambientColor=Brand.navy.copy(alpha=.20f),spotColor=Brand.navy.copy(alpha=.14f))
        .clip(RoundedCornerShape(25.dp))
        .background(Brush.linearGradient(listOf(Brand.navy,Brand.darkBlue,Brand.blue)))) {
        Canvas(Modifier.matchParentSize()) {
            drawCircle(Color.White.copy(alpha=.065f),size.width*.39f,Offset(size.width*1.05f,-size.height*.15f))
            drawCircle(Brand.cyan.copy(alpha=.17f),size.width*.29f,Offset(-size.width*.04f,size.height*.96f))
            drawCircle(Color.White.copy(alpha=.045f),size.width*.12f,Offset(size.width*.78f,size.height*.88f))
        }
        Column(Modifier.padding(20.dp),verticalArrangement=Arrangement.spacedBy(12.dp)) {
            Row(verticalAlignment=Alignment.CenterVertically) {
                Box(Modifier.size(7.dp).background(Brand.green,CircleShape))
                Spacer(Modifier.width(7.dp))
                Text(eyebrow.uppercase(),color=Color.White.copy(alpha=.8f),
                    letterSpacing=1.sp,fontSize=10.sp,fontWeight=FontWeight.Black,
                    modifier=Modifier.weight(1f))
                Icon(icon,null,tint=Color.White.copy(alpha=.92f),modifier=Modifier.size(22.dp))
            }
            Text(headline,color=Color.White,fontWeight=FontWeight.Black,fontSize=27.sp,lineHeight=31.sp)
            Text(detail,color=Color.White.copy(alpha=.78f),fontSize=12.sp,lineHeight=18.sp)
            children()
        }
    }
}
@Composable
internal fun HeroMiniStat(value:String,label:String,modifier:Modifier=Modifier) {
    Column(modifier=modifier.clip(RoundedCornerShape(13.dp))
        .background(Color.White.copy(alpha=.11f)).padding(horizontal=11.dp,vertical=10.dp),
        verticalArrangement=Arrangement.spacedBy(2.dp)) {
        Text(value,color=Color.White,fontWeight=FontWeight.Black,fontSize=16.sp,maxLines=1)
        Text(label,color=Color.White.copy(alpha=.72f),fontSize=10.sp,maxLines=1)
    }
}
@Composable
internal fun ProEmpty(icon:ImageVector,title:String,detail:String,action:String?=null,onAction:(()->Unit)?=null) {
    ProCard(Modifier.fillMaxWidth()) {
        Column(Modifier.fillMaxWidth().padding(vertical=20.dp),
            horizontalAlignment=Alignment.CenterHorizontally,
            verticalArrangement=Arrangement.spacedBy(10.dp)) {
            Box(Modifier.size(60.dp).clip(RoundedCornerShape(18.dp)).background(Brand.sky),
                contentAlignment=Alignment.Center) {
                Icon(icon,null,Modifier.size(27.dp),tint=Brand.blue)
            }
            Text(title,fontWeight=FontWeight.ExtraBold,fontSize=17.sp,color=Brand.navy)
            Text(detail,fontSize=12.sp,color=Brand.gray,lineHeight=18.sp)
            if(action!=null&&onAction!=null) OutlinedButton(onClick=onAction){Text(action)}
        }
    }
}

@Composable
internal fun ProBarRow(name:String,value:Int,maximum:Int,accent:Color=Brand.blue) {
    val fraction=(value.toFloat()/max(1,maximum)).coerceIn(0f,1f)
    val progress by animateFloatAsState(targetValue=fraction,label="analytics bar")
    Column(verticalArrangement=Arrangement.spacedBy(6.dp)) {
        Row(verticalAlignment=Alignment.CenterVertically) {
            Text(name.ifBlank{"Unknown"},fontWeight=FontWeight.SemiBold,fontSize=12.sp,
                color=Brand.navy,modifier=Modifier.weight(1f),maxLines=2,
                overflow=TextOverflow.Ellipsis,lineHeight=16.sp)
            Spacer(Modifier.width(8.dp))
            Text(value.toString(),fontWeight=FontWeight.Black,fontSize=12.sp,color=Brand.navy)
        }
        LinearProgressIndicator(progress={progress},modifier=Modifier.fillMaxWidth().height(7.dp)
            .clip(CircleShape),color=accent,trackColor=accent.copy(alpha=.10f),
            strokeCap=StrokeCap.Round)
    }
}

@Composable
internal fun TrendSpark(points:List<TrafficPoint>,modifier:Modifier=Modifier,
                        accent:Color=Brand.cyan) {
    val series=points.map {it.views.toFloat()}
    if(series.isEmpty()) {
        Box(modifier,height(0.dp)) {}
        return
    }
    Canvas(modifier.fillMaxWidth().height(125.dp)) {
        val ceiling=max(1f,series.maxOrNull()?:1f)
        val base=size.height-14.dp.toPx()
        val top=11.dp.toPx()
        val path=Path()
        val floor=Path()
        series.forEachIndexed{index,v->
            val x=if(series.size>1) size.width*index/(series.size-1) else size.width/2
            val y=base-(base-top)*(v/ceiling)
            if(index==0){path.moveTo(x,y);floor.moveTo(x,base);floor.lineTo(x,y)}
            else{path.lineTo(x,y);floor.lineTo(x,y)}
        }
        floor.lineTo(size.width,base)
        floor.close()
        drawPath(floor,brush=Brush.verticalGradient(listOf(accent.copy(alpha=.22f),accent.copy(alpha=.005f))))
        drawPath(path,accent,style=Stroke(width=2.6.dp.toPx(),cap=StrokeCap.Round))
        series.forEachIndexed { index,v ->
            val x=if(series.size>1)size.width*index/(series.size-1) else size.width/2
            val y=base-(base-top)*(v/ceiling)
            drawCircle(Color.White,4.1.dp.toPx(),Offset(x,y))
            drawCircle(accent,2.6.dp.toPx(),Offset(x,y))
        }
    }
}
@Composable
internal fun DonutDevices(items:List<Pair<String,Int>>,modifier:Modifier=Modifier) {
    val colors=listOf(Brand.blue,Brand.cyan,Brand.violet,Brand.amber,Brand.green)
    val total=items.sumOf { max(0,it.second) }
    Row(modifier=modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically,
        horizontalArrangement=Arrangement.spacedBy(18.dp)) {
        Box(Modifier.size(124.dp),contentAlignment=Alignment.Center) {
            Canvas(Modifier.fillMaxSize()) {
                var from=-90f
                if(total>0) items.forEachIndexed{index,(_,count)->
                    val sweep=360f*max(0,count)/total
                    drawArc(colors[index%colors.size],startAngle=from,sweepAngle=sweep,
                        useCenter=false,style=Stroke(width=18.dp.toPx(),cap=StrokeCap.Butt))
                    from+=sweep
                } else drawArc(Brand.sky,0f,360f,useCenter=false,
                    style=Stroke(width=18.dp.toPx()))
            }
            Column(horizontalAlignment=Alignment.CenterHorizontally) {
                Text(total.toString(),fontWeight=FontWeight.Black,fontSize=21.sp,color=Brand.navy)
                Text("Users",color=Brand.gray,fontSize=10.sp)
            }
        }
        Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(11.dp)) {
            if(items.isEmpty()) Text("No device data for this period",fontSize=12.sp,color=Brand.gray)
            items.take(5).forEachIndexed{index,item->
                Row(verticalAlignment=Alignment.CenterVertically) {
                    Box(Modifier.size(8.dp).background(colors[index%colors.size],CircleShape))
                    Spacer(Modifier.width(8.dp))
                    Text(item.first.replaceFirstChar {it.uppercase()},modifier=Modifier.weight(1f),
                        fontSize=12.sp,color=Brand.navy,maxLines=1)
                    Text((if(total>0) (item.second*100/total) else 0).toString()+"%",
                        color=Brand.gray,fontSize=12.sp,fontWeight=FontWeight.Bold)
                }
            }
        }
    }
}