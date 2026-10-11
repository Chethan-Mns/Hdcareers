plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}
fun setting(name: String): String = providers.gradleProperty(name).orNull ?: System.getenv(name) ?: ""
fun literal(value: String): String = "\"" + value.replace("\\","\\\\").replace("\"","\\\"") + "\""

android {
    namespace = "in.hdcareers.admin"
    compileSdk = 35

    defaultConfig {
        applicationId = "in.hdcareers.admin"
        minSdk = 29
        targetSdk = 35
        versionCode = 5
        versionName = "1.2.2"
        buildConfigField("String", "FIREBASE_APP_ID", literal(setting("FIREBASE_APP_ID")))
        buildConfigField("String", "FIREBASE_API_KEY", literal(setting("FIREBASE_API_KEY")))
        buildConfigField("String", "FIREBASE_PROJECT_ID", literal(setting("FIREBASE_PROJECT_ID")))
        buildConfigField("String", "FIREBASE_SENDER_ID", literal(setting("FIREBASE_SENDER_ID")))
    }
    val keystorePath = setting("HD_ANDROID_KEYSTORE_FILE")
    signingConfigs {
        create("privateRelease") {
            if (keystorePath.isNotBlank()) {
                this.storeFile = file(keystorePath)
                storePassword = setting("HD_ANDROID_KEYSTORE_PASSWORD")
                keyAlias = setting("HD_ANDROID_KEY_ALIAS")
                keyPassword = setting("HD_ANDROID_KEY_PASSWORD")
            }
        }
    }
    buildTypes {
        getByName("debug") { isMinifyEnabled = false }
        getByName("release") {
            isMinifyEnabled = false
            if (keystorePath.isNotBlank()) signingConfig = signingConfigs.getByName("privateRelease")
        }
    }
    buildFeatures { compose = true; buildConfig = true }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
    kotlinOptions { jvmTarget = "17" }
    packaging { resources { excludes += "/META-INF/{AL2.0,LGPL2.1}" } }
}
dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.12.01")
    implementation(composeBom)
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.7")
    implementation("androidx.biometric:biometric:1.1.0")
    implementation("androidx.work:work-runtime-ktx:2.10.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("io.coil-kt:coil-compose:2.7.0")
    implementation("io.coil-kt:coil-svg:2.7.0")
    implementation("com.google.firebase:firebase-messaging:24.1.0")
    debugImplementation("androidx.compose.ui:ui-tooling")
    testImplementation("junit:junit:4.13.2")
}
