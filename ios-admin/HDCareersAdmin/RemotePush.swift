import Foundation
import UIKit
import UserNotifications

extension Notification.Name {
    static let hdAPNSToken = Notification.Name("HDCareersAPNsToken")
    static let hdAPNSError = Notification.Name("HDCareersAPNsError")
    static let hdOpenReview = Notification.Name("HDCareersOpenReview")
}

final class RemotePushAppDelegate: NSObject, UIApplicationDelegate, UNUserNotificationCenterDelegate {
    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        UNUserNotificationCenter.current().delegate = self
        return true
    }

    func application(_ application: UIApplication,
                     didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
        let token = deviceToken.map { String(format: "%02x", $0) }.joined()
        DispatchQueue.main.async {
            NotificationCenter.default.post(name: .hdAPNSToken, object: token)
        }
    }

    func application(_ application: UIApplication,
                     didFailToRegisterForRemoteNotificationsWithError error: Error) {
        DispatchQueue.main.async {
            NotificationCenter.default.post(name: .hdAPNSError, object: error.localizedDescription)
        }
    }

    func userNotificationCenter(_ center: UNUserNotificationCenter,
                                willPresent notification: UNNotification) async -> UNNotificationPresentationOptions {
        return [.banner, .sound, .badge]
    }

    func userNotificationCenter(_ center: UNUserNotificationCenter,
                                didReceive response: UNNotificationResponse) async {
        let type = response.notification.request.content.userInfo["kind"] as? String
        if type == "review" || type == "test" {
            await MainActor.run {
                NotificationCenter.default.post(name: .hdOpenReview, object: nil)
            }
        }
    }
}

enum APNsInstallation {
    private static let key = "hdcareers.apns.installation.id"

    static var id: String {
        if let existing = UserDefaults.standard.string(forKey: key), !existing.isEmpty { return existing }
        let value = UUID().uuidString.lowercased()
        UserDefaults.standard.set(value, forKey: key)
        return value
    }

    static var environment: String {
        #if DEBUG
        return "development"
        #else
        return "production"
        #endif
    }
}
