package `in`.hdcareers.admin

import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import coil.request.ImageRequest
import coil.decode.SvgDecoder
import org.json.JSONObject
import java.util.Locale

private const val WEBSITE = "https://hdcareers.in/"

data class CompanyLogoSource(val path: String = "", val officialDomain: String = "")

fun parseCompanyLogoSources(manifest: JSONObject, domains: JSONObject): Map<String,CompanyLogoSource> {
    val values = mutableMapOf<String,CompanyLogoSource>()
    val names = manifest.keys()
    while(names.hasNext()) {
        val original=names.next()
        val obj=manifest.optJSONObject(original) ?: continue
        val raw=obj.optString("localPath")
        val path = if (Regex("^assets/company-icons/[a-zA-Z0-9._-]+\\.(png|webp|svg|ico)$").matches(raw)) {
            WEBSITE+raw
        } else ""
        val domain=obj.optString("officialDomain").lowercase(Locale.ROOT)
        val verified=if(validOfficialDomain(domain)) domain else ""
        if(path.isNotBlank()||verified.isNotBlank())
            values[original.trim().lowercase(Locale.ROOT)]=CompanyLogoSource(path,verified)
    }
    val keys=domains.keys()
    while(keys.hasNext()) {
        val original=keys.next()
        val domain=domains.optString(original).lowercase(Locale.ROOT)
        if(!validOfficialDomain(domain)) continue
        val key=original.trim().lowercase(Locale.ROOT)
        val earlier=values[key]
        values[key]=CompanyLogoSource(earlier?.path.orEmpty(),earlier?.officialDomain?.ifBlank { domain } ?: domain)
    }
    return values
}

private fun validOfficialDomain(domain: String): Boolean {
    if(!Regex("^[a-z0-9-]+(\\.[a-z0-9-]+)+$").matches(domain)) return false
    val generic=listOf("myworkdayjobs.com","myworkdaysite.com","greenhouse.io","lever.co",
        "oraclecloud.com","icims.com","taleo.net","smartrecruiters.com","workable.com")
    return generic.none { domain==it || domain.endsWith(".$it") }
}

private fun absoluteImageUrl(url:String):String =
    url.takeIf { it.startsWith("https://") && Uri.parse(it).host?.isNotBlank()==true }.orEmpty()

fun imageForCompany(name:String,details:JSONObject?,sources:Map<String,CompanyLogoSource>):Pair<String,String> {
    val company=name.trim().lowercase(Locale.ROOT)
    val source=sources[company]
    val direct=details?.let { detail ->
        listOf("logoUrl","companyLogoUrl","companyLogo","logoImage")
            .firstNotNullOfOrNull { key -> absoluteImageUrl(detail.optString(key)).ifBlank { null } }
    }.orEmpty()
    val primary=direct.ifBlank { source?.path.orEmpty() }
    val domain=source?.officialDomain.orEmpty()
    val favicon=if(validOfficialDomain(domain))
        "https://www.google.com/s2/favicons?domain="+Uri.encode(domain)+"&sz=128" else ""
    return Pair(primary.ifBlank { favicon }, if(primary.isNotBlank()) favicon else "")
}

@Composable
fun CompanyMark(
    name:String, sources:Map<String,CompanyLogoSource>,
    details:JSONObject?=null, size:Int=46
) {
    val (primary,backup)=remember(name,details,sources) { imageForCompany(name,details,sources) }
    var fallback by remember(primary,backup){ mutableStateOf(false) }
    var failed by remember(primary,backup){ mutableStateOf(false) }
    val current=if(fallback)backup else primary
    val shape=RoundedCornerShape(13.dp)
    Box(
        Modifier.size(size.dp).clip(shape).background(Color.White)
            .border(1.dp,Brand.outline,shape).padding(6.dp),
        contentAlignment=Alignment.Center
    ) {
        if(current.isNotBlank()&&!failed) {
            val context=LocalContext.current
            AsyncImage(
                model=ImageRequest.Builder(context).data(current)
                    .decoderFactory(SvgDecoder.Factory()).crossfade(true).build(),
                contentDescription="$name company logo",
                modifier=Modifier.size((size-12).dp),
                onError={
                    if(!fallback&&backup.isNotBlank()&&backup!=primary)fallback=true
                    else failed=true
                }
            )
        } else {
            Text(name.trim().take(2).uppercase(Locale.ROOT),fontSize=if(size>=44)14.sp else 11.sp,
                fontWeight=FontWeight.Black,color=Brand.blue)
        }
    }
}
