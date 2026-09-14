# Ktor/kotlinx.serialization utilisent la réflexion sur les classes @Serializable : à
# conserver si isMinifyEnabled passe un jour à true (désactivé par défaut, voir build.gradle.kts).
-keepattributes *Annotation*, InnerClasses
-keep,includedescriptorclasses class com.aria.phonebridge.**$$serializer { *; }
-keepclassmembers class com.aria.phonebridge.** {
    *** Companion;
}
-keepclasseswithmembers class com.aria.phonebridge.** {
    kotlinx.serialization.KSerializer serializer(...);
}
