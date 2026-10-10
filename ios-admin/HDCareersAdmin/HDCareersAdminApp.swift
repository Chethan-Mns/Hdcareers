import SwiftUI
import UIKit
import UserNotifications

@MainActor
final class AppState: ObservableObject {
    @Published var isBootstrapping = false
    @Published var isAuthenticated = false
    @Published var isBusy = false
    @Published var alertMessage: String?
    @Published var loginStatus: String?
    @Published var jobs: [Job] = []
    @Published var traffic: TrafficResponse?
    @Published var automationHealth: AutomationHealth?
    @Published var availability: AvailabilityResponse?
    @Published var trafficDays = 7
    @Published var dailyBatch: DailyBatch?
    @Published var isBatchBusy = false
    @Published var selectedTab = 0
    @Published var pushStatus = "Remote push not enabled"

    let api = APIClient.shared

    var activeJobs: [Job] { jobs.filter(\.isActive) }
    var expiredJobs: [Job] { jobs.filter(\.isExpired) }
    var fresherJobs: [Job] { activeJobs.filter(\.isFresher) }
    var experiencedJobs: [Job] { activeJobs.filter { !$0.isFresher } }

    func bootstrap() async {
        isBootstrapping = false

        do {
            let authenticated = try await api.sessionStatus()
            if authenticated {
                isAuthenticated = true
                Task { @MainActor in
                    await refreshAll()
                    await restoreRemotePushIfEnabled()
                }
            }
        } catch {
            isAuthenticated = false
        }
    }

    func login(username: String, password: String, rememberWithFaceID: Bool) async {
        loginStatus = nil
        let user = username.trimmingCharacters(in: .whitespacesAndNewlines)

        guard !user.isEmpty, !password.isEmpty else {
            loginStatus = "Enter your admin username and password."
            return
        }

        isBusy = true
        defer { isBusy = false }

        do {
            try await api.login(username: user, password: password)
            isAuthenticated = true
            await restoreRemotePushIfEnabled()

            if rememberWithFaceID && BiometricAuth.isAvailable {
                do {
                    try CredentialVault.save(username: user, password: password)
                } catch {
                    alertMessage = "Signed in successfully, but Face ID could not be enabled on this iPhone."
                }
            }

            Task { @MainActor in
                await refreshAll()
            }
        } catch {
            loginStatus = error.localizedDescription
        }
    }

    func faceIDLogin() async {
        guard let credential = CredentialVault.load() else {
            alertMessage = "No Face ID login is saved on this iPhone yet."
            return
        }

        isBusy = true
        defer { isBusy = false }

        do {
            try await BiometricAuth.authenticate()
            try await api.login(username: credential.username, password: credential.password)
            isAuthenticated = true
            await restoreRemotePushIfEnabled()
            Task { @MainActor in
                await refreshAll()
            }
        } catch {
            alertMessage = error.localizedDescription
        }
    }

    func logout() async {
        try? await api.unregisterPush()
        await api.logout()
        isAuthenticated = false
        jobs = []
        traffic = nil
        automationHealth = nil
        availability = nil
        dailyBatch = nil
    }

    func removeSavedFaceID() {
        CredentialVault.delete()
        alertMessage = "Saved Face ID credentials were removed from this iPhone."
    }

    func refreshAll() async {
        isBusy = true
        defer { isBusy = false }

        var firstError: String?

        do { jobs = try await api.jobs() }
        catch { firstError = firstError ?? error.localizedDescription }

        do { traffic = try await api.traffic(days: trafficDays) }
        catch { firstError = firstError ?? error.localizedDescription }

        do { automationHealth = try await api.automationHealth() }
        catch { firstError = firstError ?? error.localizedDescription }

        do { availability = try await api.availability() }
        catch { firstError = firstError ?? error.localizedDescription }

        do { dailyBatch = try await api.dailyBatch() }
        catch { firstError = firstError ?? error.localizedDescription }

        if let firstError {
            alertMessage = firstError
        }
    }

    func loadTraffic(days: Int) async {
        trafficDays = days
        do {
            traffic = try await api.traffic(days: days)
        } catch {
            alertMessage = error.localizedDescription
        }
    }

    func refreshJobs() async {
        do {
            jobs = try await api.jobs()
        } catch {
            alertMessage = error.localizedDescription
        }
    }

    func refreshChecker() async {
        do {
            availability = try await api.availability()
        } catch {
            alertMessage = error.localizedDescription
        }
    }

    func runChecker() async {
        isBusy = true
        defer { isBusy = false }

        do {
            let response = try await api.runChecker()
            alertMessage = response.message ?? "Expired-job checker queued."
            try? await Task.sleep(for: .seconds(2))
            await refreshChecker()
        } catch {
            alertMessage = error.localizedDescription
        }
    }

    func resolveReview(_ item: AvailabilityItem, action: String) async {
        guard let id = item.jobId else {
            alertMessage = "This review item has no job ID."
            return
        }

        isBusy = true
        defer { isBusy = false }

        do {
            let response = try await api.resolveReview(jobId: id, action: action)
            alertMessage = response.message
            await refreshChecker()
            await refreshJobs()
        } catch {
            alertMessage = error.localizedDescription
        }
    }
    func refreshDailyBatch() async {
        do {
            dailyBatch = try await api.dailyBatch()
        } catch {
            alertMessage = error.localizedDescription
        }
    }

    func setDailyDecision(candidateId: String, decision: String) async {
        guard let batchId = dailyBatch?.batchId, !batchId.isEmpty else { return }
        isBatchBusy = true
        defer { isBatchBusy = false }
        do {
            dailyBatch = try await api.reviewDailyBatch(batchId: batchId, candidateId: candidateId, decision: decision)
        } catch {
            alertMessage = error.localizedDescription
            await refreshDailyBatch()
        }
    }

    func swapDailyCandidate(priorityId: String, backupId: String) async {
        guard let batchId = dailyBatch?.batchId, !batchId.isEmpty else { return }
        isBatchBusy = true
        defer { isBatchBusy = false }
        do {
            dailyBatch = try await api.replaceDailyBatch(batchId: batchId, priorityId: priorityId, backupId: backupId)
        } catch {
            alertMessage = error.localizedDescription
            await refreshDailyBatch()
        }
    }

    func publishDailyBatch() async {
        guard let batch = dailyBatch, batch.readyToPublish else {
            alertMessage = "Review all ten priority jobs as Live and complete their verified descriptions before publishing."
            return
        }
        let jobs = batch.priority.compactMap(\.job)
        guard jobs.count == 10 else {
            alertMessage = "Some job descriptions are incomplete."
            return
        }
        isBatchBusy = true
        defer { isBatchBusy = false }
        do {
            let response = try await api.publish(jobs: jobs)
            dailyBatch = try await api.markDailyBatchSubmitted(batchId: batch.batchId)
            alertMessage = response.message ?? "Publishing request accepted. Check deployment and Telegram status."
        } catch {
            alertMessage = error.localizedDescription + " If a publishing request succeeded, check GitHub before retrying."
            await refreshDailyBatch()
        }
    }
    private let pushEnabledKey = "hdcareers.apns.user-enabled"

    func enableRemotePush() async {
        guard isAuthenticated else { alertMessage = "Sign in first to enable push notifications."; return }
        do {
            let config = try await api.pushConfiguration()
            guard config.configured else {
                alertMessage = "Apple APNs and private device storage must be configured on the server first."
                return
            }
            let center = UNUserNotificationCenter.current()
            let granted = try await center.requestAuthorization(options: [.alert, .badge, .sound])
            guard granted else {
                alertMessage = "Allow notifications for HD Careers Admin in iPhone Settings."
                return
            }
            UserDefaults.standard.set(true, forKey: pushEnabledKey)
            pushStatus = "Requesting your Apple device token..."
            UIApplication.shared.registerForRemoteNotifications()
        } catch {
            alertMessage = error.localizedDescription
        }
    }

    func restoreRemotePushIfEnabled() async {
        guard UserDefaults.standard.bool(forKey: pushEnabledKey), isAuthenticated else { return }
        let status = await UNUserNotificationCenter.current().notificationSettings()
        guard status.authorizationStatus == .authorized || status.authorizationStatus == .provisional else { return }
        UIApplication.shared.registerForRemoteNotifications()
    }

    func uploadPushToken(_ token: String) async {
        guard UserDefaults.standard.bool(forKey: pushEnabledKey), isAuthenticated else { return }
        do {
            try await api.registerPushToken(token)
            pushStatus = "Device registered for push notifications"
        } catch {
            pushStatus = "Push registration needs attention"
            alertMessage = error.localizedDescription
        }
    }

    func disableRemotePush() async {
        do {
            try await api.unregisterPush()
            UserDefaults.standard.set(false, forKey: pushEnabledKey)
            UIApplication.shared.unregisterForRemoteNotifications()
            pushStatus = "Remote push disabled"
        } catch {
            alertMessage = error.localizedDescription
        }
    }

    func sendTestPush() async {
        do {
            let sent = try await api.sendPushTest()
            alertMessage = sent ? "APNs accepted the test. Check your iPhone's notification settings if no banner appears." : "APNs could not deliver the test. Check the server's push credentials."
        } catch {
            alertMessage = error.localizedDescription
        }
    }
}

@main
struct HDCareersAdminApp: App {
    @StateObject private var state = AppState()
    @Environment(\.scenePhase) private var scenePhase
    @UIApplicationDelegateAdaptor(RemotePushAppDelegate.self) private var pushDelegate

    var body: some Scene {
        WindowGroup {
            ZStack {
                HDTheme.background.ignoresSafeArea()
                if state.isAuthenticated {
                    RootTabView()
                } else {
                    LoginView()
                }
            }
            .environmentObject(state)
            .tint(HDTheme.blue)
            .preferredColorScheme(.light)
            .task {
                await state.bootstrap()
            }
            .onChange(of: scenePhase) { _, phase in
                if phase == .active && state.isAuthenticated {
                    Task {
                        await state.refreshDailyBatch()
                        await state.restoreRemotePushIfEnabled()
                    }
                }
            }
            .onReceive(NotificationCenter.default.publisher(for: .hdAPNSToken)) { notice in
                if let token = notice.object as? String {
                    Task { await state.uploadPushToken(token) }
                }
            }
            .onReceive(NotificationCenter.default.publisher(for: .hdAPNSError)) { notice in
                state.pushStatus = "Apple device registration failed"
                state.alertMessage = "Unable to register with APNs: " + (notice.object as? String ?? "Unknown error")
            }
            .onReceive(NotificationCenter.default.publisher(for: .hdOpenReview)) { _ in
                state.selectedTab = 2
            }
            .alert("HD Careers Admin", isPresented: Binding(
                get: { state.alertMessage != nil },
                set: { if !$0 { state.alertMessage = nil } }
            )) {
                Button("OK", role: .cancel) { state.alertMessage = nil }
            } message: {
                Text(state.alertMessage ?? "")
            }
        }
    }
}

struct LaunchView: View {
    var body: some View {
        ZStack {
            HDTheme.background.ignoresSafeArea()
            VStack(spacing: 18) {
                HDLogoView(size: 82)
                Text("HD Careers Admin")
                    .font(.title2.bold())
                    .foregroundStyle(HDTheme.navy)
                ProgressView()
            }
        }
    }
}
