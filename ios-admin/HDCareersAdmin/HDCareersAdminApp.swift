import SwiftUI

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
            Task { @MainActor in
                await refreshAll()
            }
        } catch {
            alertMessage = error.localizedDescription
        }
    }

    func logout() async {
        await api.logout()
        isAuthenticated = false
        jobs = []
        traffic = nil
        automationHealth = nil
        availability = nil
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
}

@main
struct HDCareersAdminApp: App {
    @StateObject private var state = AppState()

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
