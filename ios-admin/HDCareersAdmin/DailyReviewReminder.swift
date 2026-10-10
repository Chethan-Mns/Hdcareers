import Foundation
import UserNotifications

enum DailyReviewReminder {
    static func enable() async throws {
        let center = UNUserNotificationCenter.current()
        let granted = try await center.requestAuthorization(options: [.alert, .badge, .sound])
        guard granted else {
            throw NSError(domain: "HDCareersNotifications", code: 1,
                          userInfo: [NSLocalizedDescriptionKey: "Notifications are disabled. Enable them in iPhone Settings for HD Careers Admin."])
        }

        let content = UNMutableNotificationContent()
        content.title = "HD Careers · Daily Review"
        content.body = "Check whether today's priority 10 and backup 10 jobs are ready for approval."
        content.sound = .default

        var date = DateComponents()
        date.calendar = Calendar(identifier: .gregorian)
        date.timeZone = TimeZone(identifier: "Asia/Kolkata")
        date.hour = 9
        date.minute = 15

        let trigger = UNCalendarNotificationTrigger(dateMatching: date, repeats: true)
        let request = UNNotificationRequest(identifier: "hdcareers-daily-review", content: content, trigger: trigger)
        try await center.add(request)
    }

    static func disable() {
        UNUserNotificationCenter.current().removePendingNotificationRequests(withIdentifiers: ["hdcareers-daily-review"])
    }
}