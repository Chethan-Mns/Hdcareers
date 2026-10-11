package `in`.hdcareers.admin

import android.Manifest
import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkerParameters
import androidx.work.WorkManager
import com.google.firebase.FirebaseApp
import com.google.firebase.FirebaseOptions
import com.google.firebase.messaging.FirebaseMessaging
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import java.time.Duration
import java.time.ZonedDateTime
import java.time.ZoneId
import java.util.UUID
import java.util.concurrent.TimeUnit

const val REVIEW_CHANNEL="hd_review_updates"
const val REMINDER_CHANNEL="hd_daily_reminder"

class HDApplication:Application() {
    override fun onCreate() {
        super.onCreate()
        val manager=getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.createNotificationChannel(NotificationChannel(REVIEW_CHANNEL,"Job batches and publishing",NotificationManager.IMPORTANCE_HIGH))
        manager.createNotificationChannel(NotificationChannel(REMINDER_CHANNEL,"Daily pending reviews",NotificationManager.IMPORTANCE_DEFAULT))
        if (BuildConfig.FIREBASE_APP_ID.isNotBlank() && BuildConfig.FIREBASE_API_KEY.isNotBlank() &&
            BuildConfig.FIREBASE_SENDER_ID.isNotBlank() && BuildConfig.FIREBASE_PROJECT_ID.isNotBlank()) {
            if (FirebaseApp.getApps(this).isEmpty()) {
                FirebaseApp.initializeApp(this,FirebaseOptions.Builder()
                    .setApplicationId(BuildConfig.FIREBASE_APP_ID).setApiKey(BuildConfig.FIREBASE_API_KEY)
                    .setGcmSenderId(BuildConfig.FIREBASE_SENDER_ID)
                    .setProjectId(BuildConfig.FIREBASE_PROJECT_ID).build())
            }
        }
        ReminderWorker.schedule(this)
    }
}
fun installationId(context:Context):String {
    val prefs=context.getSharedPreferences("hd_installation",Context.MODE_PRIVATE)
    val existing=prefs.getString("id",null)
    if(existing!=null) return existing
    val id=UUID.randomUUID().toString()
    prefs.edit().putString("id",id).apply()
    return id
}
fun firebaseReady(context:Context):Boolean = FirebaseApp.getApps(context).isNotEmpty()
fun fcmToken(context:Context,onToken:(String)->Unit,onError:(String)->Unit) {
    if(!firebaseReady(context)) { onError("Firebase client configuration is not installed yet."); return }
    FirebaseMessaging.getInstance().token.addOnSuccessListener(onToken).addOnFailureListener {
        onError(it.localizedMessage ?: "FCM token unavailable.")
    }
}
fun showHDNotification(context:Context,title:String,body:String,channel:String,id:Int) {
    if(Build.VERSION.SDK_INT>=33 &&
        context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED) return
    val intent=Intent(context,MainActivity::class.java).apply {
        flags=Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP
        putExtra("open_review",true)
    }
    val pending=PendingIntent.getActivity(context,100,intent,
        PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
    val item=NotificationCompat.Builder(context,channel)
        .setSmallIcon(R.drawable.ic_launcher)
        .setContentTitle(title).setContentText(body)
        .setAutoCancel(true).setContentIntent(pending)
        .setPriority(if(channel==REVIEW_CHANNEL)NotificationCompat.PRIORITY_HIGH else NotificationCompat.PRIORITY_DEFAULT)
        .build()
    NotificationManagerCompat.from(context).notify(id,item)
}
class PushService:FirebaseMessagingService() {
    override fun onNewToken(token:String) {
        super.onNewToken(token)
        getSharedPreferences("hd_push",MODE_PRIVATE).edit().putString("token",token).apply()
    }
    override fun onMessageReceived(message:RemoteMessage) {
        val title=message.notification?.title ?: message.data["title"] ?: "HD Careers"
        val body=message.notification?.body ?: message.data["body"] ?: "Your job review has an update."
        showHDNotification(this,title,body,REVIEW_CHANNEL,
            message.data["batchId"]?.hashCode() ?: System.currentTimeMillis().toInt())
    }
}
class ReminderWorker(context:Context,params:WorkerParameters):CoroutineWorker(context,params) {
    override suspend fun doWork():Result {
        val prefs=applicationContext.getSharedPreferences("hd_review",Context.MODE_PRIVATE)
        if(prefs.getBoolean("reminder_enabled",true) && prefs.getBoolean("pending",false)) {
            showHDNotification(applicationContext,"HD Careers · Review pending",
                "Your last synced job batch still needs a review.",REMINDER_CHANNEL,99201)
        }
        return Result.success()
    }
    companion object {
        fun schedule(context:Context) {
            val zone=ZoneId.of("Asia/Kolkata")
            val now=ZonedDateTime.now(zone)
            var target=now.withHour(9).withMinute(30).withSecond(0).withNano(0)
            if(!target.isAfter(now)) target=target.plusDays(1)
            val delay=Duration.between(now,target).toMillis()
            val work=PeriodicWorkRequestBuilder<ReminderWorker>(24,TimeUnit.HOURS)
                .setInitialDelay(delay,TimeUnit.MILLISECONDS).build()
            WorkManager.getInstance(context).enqueueUniquePeriodicWork("hd_daily_pending_review",
                ExistingPeriodicWorkPolicy.KEEP,work)
        }
    }
}
