import SwiftUI
import Charts

private func numberText(_ value: Int?) -> String {
    NumberFormatter.localizedString(from: NSNumber(value: value ?? 0), number: .decimal)
}

private func formatAdminDate(_ value: String?) -> String {
    guard let value, !value.isEmpty else { return "Never" }
    let formatter = ISO8601DateFormatter()
    formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
    var date = formatter.date(from: value)
    if date == nil {
        formatter.formatOptions = [.withInternetDateTime]
        date = formatter.date(from: value)
    }
    guard let date else { return value }

    let display = DateFormatter()
    display.locale = Locale(identifier: "en_IN")
    display.timeZone = TimeZone(identifier: "Asia/Kolkata")
    display.dateFormat = "dd MMM yyyy, h:mm a"
    return display.string(from: date)
}

private func siteURL(_ path: String?) -> URL? {
    guard let path, !path.isEmpty else { return nil }
    if let absolute = URL(string: path), absolute.scheme != nil { return absolute }
    return URL(string: "https://hdcareers.in/" + path.trimmingCharacters(in: CharacterSet(charactersIn: "/")))
}

private func jobDisplayName(path: String?, jobs: [Job]) -> String {
    guard let path else { return "HD Careers Home" }
    if path == "/" || path == "/index.html" { return "HD Careers Home" }
    let normalized = path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
    if let job = jobs.first(where: { ($0.page ?? "").trimmingCharacters(in: CharacterSet(charactersIn: "/")) == normalized }) {
        return "\(job.company ?? "Job") — \(job.role ?? "Opening")"
    }
    return normalized
        .replacingOccurrences(of: "jobs/", with: "")
        .replacingOccurrences(of: ".html", with: "")
        .replacingOccurrences(of: "-", with: " ")
        .capitalized
}


struct PremiumSectionTitle: View {
    let icon: String
    let title: String
    let subtitle: String?
    var color: Color = HDTheme.blue

    init(icon: String, title: String, subtitle: String? = nil, color: Color = HDTheme.blue) {
        self.icon = icon
        self.title = title
        self.subtitle = subtitle
        self.color = color
    }

    var body: some View {
        HStack(spacing: 11) {
            Image(systemName: icon)
                .font(.system(size: 13, weight: .bold))
                .foregroundStyle(color)
                .frame(width: 34, height: 34)
                .background(color.opacity(0.10))
                .clipShape(RoundedRectangle(cornerRadius: 11, style: .continuous))

            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.subheadline.weight(.black))
                    .foregroundStyle(HDTheme.navy)
                if let subtitle {
                    Text(subtitle)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }

            Spacer()
        }
    }
}

struct PremiumMetricTile: View {
    let title: String
    let value: String
    let icon: String
    let color: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: icon)
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(color)
                    .frame(width: 30, height: 30)
                    .background(color.opacity(0.10))
                    .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                Spacer()
            }

            Text(value)
                .font(.system(size: 22, weight: .black, design: .rounded))
                .foregroundStyle(HDTheme.navy)
                .lineLimit(1)
                .minimumScaleFactor(0.75)

            Text(title)
                .font(.caption2.weight(.bold))
                .foregroundStyle(.secondary)
                .lineLimit(1)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(color.opacity(0.055))
        .clipShape(RoundedRectangle(cornerRadius: 15, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 15, style: .continuous)
                .stroke(color.opacity(0.10))
        }
    }
}

struct PremiumMetaChip: View {
    let text: String
    let icon: String
    var color: Color = HDTheme.blue

    var body: some View {
        Label(text, systemImage: icon)
            .font(.system(size: 9.5, weight: .bold))
            .foregroundStyle(color)
            .padding(.horizontal, 8)
            .padding(.vertical, 5)
            .background(color.opacity(0.08))
            .clipShape(Capsule())
    }
}

struct PremiumBarRow: View {
    let title: String
    let value: Int
    let maxValue: Int
    var color: Color = HDTheme.blue

    var body: some View {
        VStack(spacing: 5) {
            HStack {
                Text(title)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(HDTheme.navy)
                    .lineLimit(1)
                Spacer()
                Text(numberText(value))
                    .font(.caption.weight(.black))
                    .foregroundStyle(HDTheme.navy)
            }

            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    Capsule().fill(Color.black.opacity(0.055))
                    Capsule()
                        .fill(
                            LinearGradient(
                                colors: [color, color.opacity(0.55)],
                                startPoint: .leading,
                                endPoint: .trailing
                            )
                        )
                        .frame(width: geo.size.width * CGFloat(value) / CGFloat(max(maxValue, 1)))
                }
            }
            .frame(height: 5)
        }
    }
}

struct PremiumInfoBox: View {
    let icon: String
    let title: String
    let text: String
    var color: Color = HDTheme.blue

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: icon)
                .font(.system(size: 12, weight: .bold))
                .foregroundStyle(color)
                .frame(width: 30, height: 30)
                .background(color.opacity(0.10))
                .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))

            VStack(alignment: .leading, spacing: 3) {
                Text(title)
                    .font(.caption.weight(.black))
                    .foregroundStyle(HDTheme.navy)
                Text(text)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            Spacer(minLength: 0)
        }
        .padding(11)
        .background(color.opacity(0.045))
        .clipShape(RoundedRectangle(cornerRadius: 13, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 13, style: .continuous)
                .stroke(color.opacity(0.12))
        }
    }
}

struct PublishWorkflowStep: View {
    let number: String
    let title: String
    let icon: String
    let active: Bool

    var body: some View {
        VStack(spacing: 7) {
            ZStack {
                Circle()
                    .fill(active ? HDTheme.blue : Color.white.opacity(0.18))
                    .frame(width: 36, height: 36)
                Image(systemName: icon)
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(.white)
            }

            Text(title)
                .font(.system(size: 9, weight: .bold))
                .foregroundStyle(.white.opacity(active ? 0.98 : 0.70))
                .lineLimit(1)
        }
        .frame(maxWidth: .infinity)
    }
}

struct PremiumField: View {
    let title: String
    let icon: String
    @Binding var text: String

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Label(title, systemImage: icon)
                .font(.caption2.weight(.bold))
                .foregroundStyle(.secondary)

            TextField(title, text: $text)
                .textInputAutocapitalization(.sentences)
                .padding(.horizontal, 12)
                .frame(height: 44)
                .background(Color(.secondarySystemBackground))
                .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        }
    }
}

struct PremiumTextEditorField: View {
    let title: String
    let icon: String
    let hint: String
    @Binding var text: String
    var minHeight: CGFloat = 104
    var color: Color = HDTheme.blue

    var body: some View {
        VStack(alignment: .leading, spacing: 9) {
            HStack(spacing: 9) {
                Image(systemName: icon)
                    .font(.system(size: 11, weight: .bold))
                    .foregroundStyle(color)
                    .frame(width: 28, height: 28)
                    .background(color.opacity(0.10))
                    .clipShape(RoundedRectangle(cornerRadius: 9, style: .continuous))

                VStack(alignment: .leading, spacing: 1) {
                    Text(title)
                        .font(.caption.weight(.black))
                        .foregroundStyle(HDTheme.navy)
                    Text(hint)
                        .font(.system(size: 9.5))
                        .foregroundStyle(.secondary)
                }
            }

            TextEditor(text: $text)
                .font(.subheadline)
                .frame(minHeight: minHeight)
                .padding(9)
                .scrollContentBackground(.hidden)
                .background(Color(.secondarySystemBackground))
                .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        }
        .padding(12)
        .background(Color.white)
        .clipShape(RoundedRectangle(cornerRadius: 15, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 15, style: .continuous)
                .stroke(Color.black.opacity(0.055))
        }
    }
}

struct LoginView: View {
    @EnvironmentObject private var state: AppState
    @State private var username = ""
    @State private var password = ""
    @State private var rememberWithFaceID = false

    private var canUseFaceID: Bool {
        BiometricAuth.isAvailable
    }

    private var hasSavedCredential: Bool {
        CredentialVault.load() != nil
    }

    var body: some View {
        ZStack {
            LinearGradient(
                colors: [.white, HDTheme.background, HDTheme.blue.opacity(0.08)],
                startPoint: .top,
                endPoint: .bottom
            )
            .ignoresSafeArea()

            ScrollView {
                VStack(spacing: 28) {
                    Spacer(minLength: 64)

                    VStack(spacing: 14) {
                        HDLogoView(size: 92)
                        Text("HD Careers Admin")
                            .font(.system(size: 28, weight: .black, design: .rounded))
                            .foregroundStyle(HDTheme.navy)
                        Text("Private control center for jobs, automations and analytics.")
                            .font(.subheadline)
                            .multilineTextAlignment(.center)
                            .foregroundStyle(.secondary)
                            .padding(.horizontal)
                    }

                    VStack(spacing: 14) {
                        HStack {
                            Image(systemName: "person.fill")
                                .foregroundStyle(.secondary)
                            TextField("Admin username", text: $username)
                                .textInputAutocapitalization(.never)
                                .autocorrectionDisabled()
                                .textContentType(.username)
                        }
                        .padding()
                        .background(Color.white)
                        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
                        .overlay {
                            RoundedRectangle(cornerRadius: 16, style: .continuous)
                                .stroke(Color.black.opacity(0.08))
                        }

                        HStack {
                            Image(systemName: "lock.fill")
                                .foregroundStyle(.secondary)
                            SecureField("Password", text: $password)
                                .textContentType(.password)
                                .submitLabel(.go)
                                .onSubmit {
                                    Task {
                                        await state.login(
                                            username: username,
                                            password: password,
                                            rememberWithFaceID: rememberWithFaceID
                                        )
                                    }
                                }
                        }
                        .padding()
                        .background(Color.white)
                        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
                        .overlay {
                            RoundedRectangle(cornerRadius: 16, style: .continuous)
                                .stroke(Color.black.opacity(0.08))
                        }

                        if let loginStatus = state.loginStatus, !loginStatus.isEmpty {
                            HStack(alignment: .top, spacing: 8) {
                                Image(systemName: "exclamationmark.circle.fill")
                                    .foregroundStyle(HDTheme.red)
                                Text(loginStatus)
                                    .font(.footnote.weight(.semibold))
                                    .foregroundStyle(HDTheme.red)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                            }
                            .padding(11)
                            .background(HDTheme.red.opacity(0.08))
                            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                        }

                        if canUseFaceID {
                            Toggle(isOn: $rememberWithFaceID) {
                                Label("Enable Face ID on this iPhone", systemImage: "faceid")
                                    .font(.footnote.weight(.semibold))
                            }
                            .tint(HDTheme.blue)
                        }

                        Button {
                            Task {
                                await state.login(
                                    username: username,
                                    password: password,
                                    rememberWithFaceID: rememberWithFaceID
                                )
                            }
                        } label: {
                            HStack {
                                if state.isBusy {
                                    ProgressView().tint(.white)
                                }
                                Text(state.isBusy ? "Signing in…" : "Sign In")
                                    .fontWeight(.bold)
                            }
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 15)
                        }
                        .buttonStyle(.plain)
                        .foregroundStyle(.white)
                        .background(HDTheme.blue)
                        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
                        .disabled(state.isBusy)

                        if canUseFaceID && hasSavedCredential {
                            Button {
                                Task { await state.faceIDLogin() }
                            } label: {
                                Label("Unlock with Face ID", systemImage: "faceid")
                                    .fontWeight(.bold)
                                    .frame(maxWidth: .infinity)
                                    .padding(.vertical, 14)
                            }
                            .buttonStyle(.plain)
                            .foregroundStyle(HDTheme.blue)
                            .background(HDTheme.blue.opacity(0.08))
                            .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
                        }
                    }
                    .hdCard(18)

                    Label("Private Admin Access", systemImage: "lock.shield")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.secondary)

                    Spacer(minLength: 30)
                }
                .padding(.horizontal, 20)
            }
        }
    }
}

struct RootTabView: View {
    @EnvironmentObject private var state: AppState
    @State private var selection = 0

    var body: some View {
        TabView(selection: $selection) {
            DashboardView()
                .tabItem { Label("Dashboard", systemImage: "house.fill") }
                .tag(0)

            JobsView()
                .tabItem { Label("Jobs", systemImage: "briefcase.fill") }
                .tag(1)

            PublishView()
                .tabItem { Label("Publish", systemImage: "wand.and.stars") }
                .tag(2)

            CheckerView()
                .tabItem { Label("Checker", systemImage: "checkmark.shield.fill") }
                .tag(3)

            MoreView()
                .tabItem { Label("More", systemImage: "ellipsis") }
                .tag(4)
        }
        .tint(HDTheme.blue)
    }
}

struct AdminHeader: View {
    let title: String
    var subtitle: String? = nil
    var trailingSystemImage: String? = nil
    var trailingAction: (() -> Void)? = nil

    var body: some View {
        HStack(spacing: 12) {
            HDLogoView(size: 42)
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.headline.weight(.black))
                    .foregroundStyle(HDTheme.navy)
                if let subtitle {
                    Text(subtitle)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            Spacer()
            if let trailingSystemImage, let trailingAction {
                Button(action: trailingAction) {
                    Image(systemName: trailingSystemImage)
                        .font(.system(size: 16, weight: .bold))
                        .frame(width: 38, height: 38)
                        .background(HDTheme.blue.opacity(0.08))
                        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                }
                .buttonStyle(.plain)
            }
        }
    }
}

struct DashboardView: View {
    @EnvironmentObject private var state: AppState

    var body: some View {
        NavigationStack {
            ZStack {
                HDTheme.background.ignoresSafeArea()

                ScrollView {
                    VStack(spacing: 12) {
                        AdminHeader(
                            title: "HD Careers Admin",
                            subtitle: "Jobs, publishing and traffic",
                            trailingSystemImage: "arrow.clockwise"
                        ) {
                            Task { await state.refreshAll() }
                        }

                        DashboardHeroCard()
                        ReviewAlertCard()
                        DashboardStatsCard()
                        TrafficSummaryCard()
                        AutomationHealthCard()
                    }
                    .padding(.horizontal, 16)
                    .padding(.top, 12)
                    .padding(.bottom, 18)
                }
                .refreshable { await state.refreshAll() }
            }
            .toolbar(.hidden, for: .navigationBar)
        }
    }
}

struct DashboardHeroCard: View {
    @EnvironmentObject private var state: AppState

    private var reviewCount: Int {
        state.availability?.results?.items?.filter { $0.state == "review" }.count ?? 0
    }

    private var publishingTime: String {
        state.automationHealth?.slots.first(where: { $0.enabled })?.time ?? "09:00"
    }

    var body: some View {
        ZStack {
            LinearGradient(
                colors: [HDTheme.navy, Color(red: 0.04, green: 0.25, blue: 0.55), HDTheme.blue],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )

            Circle()
                .fill(Color.white.opacity(0.08))
                .frame(width: 180, height: 180)
                .offset(x: 140, y: -72)

            Circle()
                .fill(HDTheme.cyan.opacity(0.12))
                .frame(width: 120, height: 120)
                .offset(x: -145, y: 85)

            VStack(alignment: .leading, spacing: 15) {
                HStack {
                    HStack(spacing: 7) {
                        Circle()
                            .fill(HDTheme.green)
                            .frame(width: 7, height: 7)
                        Text("OPERATIONS LIVE")
                            .font(.system(size: 10, weight: .black))
                            .tracking(1.1)
                    }
                    .foregroundStyle(.white.opacity(0.84))

                    Spacer()

                    Image(systemName: "sparkles")
                        .font(.system(size: 15, weight: .bold))
                        .foregroundStyle(.white.opacity(0.9))
                }

                VStack(alignment: .leading, spacing: 4) {
                    Text("Everything important,")
                        .font(.system(size: 15, weight: .semibold))
                        .foregroundStyle(.white.opacity(0.78))
                    Text("under control.")
                        .font(.system(size: 31, weight: .black, design: .rounded))
                        .foregroundStyle(.white)
                }

                HStack(spacing: 8) {
                    heroStat(icon: "briefcase.fill", value: "\\(state.activeJobs.count)", label: "Live")
                    heroStat(icon: reviewCount > 0 ? "exclamationmark.triangle.fill" : "checkmark.shield.fill", value: "\\(reviewCount)", label: "Review")
                    heroStat(icon: "clock.fill", value: publishingTime, label: "Publish")
                }
            }
            .padding(20)
        }
        .frame(height: 202)
        .clipShape(RoundedRectangle(cornerRadius: 26, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 26, style: .continuous)
                .stroke(Color.white.opacity(0.12))
        }
        .shadow(color: HDTheme.navy.opacity(0.16), radius: 18, x: 0, y: 10)
    }

    private func heroStat(icon: String, value: String, label: String) -> some View {
        HStack(spacing: 7) {
            Image(systemName: icon)
                .font(.system(size: 10, weight: .bold))
                .foregroundStyle(.white.opacity(0.9))
            VStack(alignment: .leading, spacing: 0) {
                Text(value)
                    .font(.caption.weight(.black))
                    .foregroundStyle(.white)
                    .lineLimit(1)
                Text(label)
                    .font(.system(size: 8.5, weight: .semibold))
                    .foregroundStyle(.white.opacity(0.62))
            }
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.white.opacity(0.10))
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
    }
}

struct ReviewAlertCard: View {
    @EnvironmentObject private var state: AppState

    private var reviewItems: [AvailabilityItem] {
        state.availability?.results?.items?.filter { $0.state == "review" } ?? []
    }

    var body: some View {
        if !reviewItems.isEmpty {
            NavigationLink {
                CheckerView()
            } label: {
                HStack(spacing: 14) {
                    Image(systemName: "bell.badge.fill")
                        .font(.system(size: 22, weight: .bold))
                        .foregroundStyle(HDTheme.amber)
                        .frame(width: 46, height: 46)
                        .background(HDTheme.amber.opacity(0.12))
                        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))

                    VStack(alignment: .leading, spacing: 3) {
                        Text("\(reviewItems.count) job\(reviewItems.count == 1 ? "" : "s") need your review")
                            .font(.headline.weight(.black))
                            .foregroundStyle(HDTheme.navy)
                        Text("Open the official page, verify it, then keep active or mark expired.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .multilineTextAlignment(.leading)
                    }
                    Spacer()
                    Image(systemName: "chevron.right")
                        .foregroundStyle(HDTheme.amber)
                }
                .padding(15)
                .background(HDTheme.amber.opacity(0.07))
                .overlay {
                    RoundedRectangle(cornerRadius: 18, style: .continuous)
                        .stroke(HDTheme.amber.opacity(0.22))
                }
                .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
            }
            .buttonStyle(.plain)
        }
    }
}

struct DashboardStatsCard: View {
    @EnvironmentObject private var state: AppState
    private let columns = [GridItem(.flexible()), GridItem(.flexible())]

    var body: some View {
        VStack(alignment: .leading, spacing: 13) {
            PremiumSectionTitle(
                icon: "square.grid.2x2.fill",
                title: "Jobs overview",
                subtitle: "Current publishing inventory"
            )

            LazyVGrid(columns: columns, spacing: 9) {
                PremiumMetricTile(title: "Total jobs", value: numberText(state.jobs.count), icon: "briefcase.fill", color: HDTheme.blue)
                PremiumMetricTile(title: "Freshers", value: numberText(state.fresherJobs.count), icon: "person.crop.circle.badge.checkmark", color: HDTheme.violet)
                PremiumMetricTile(title: "Active", value: numberText(state.activeJobs.count), icon: "checkmark.circle.fill", color: HDTheme.green)
                PremiumMetricTile(title: "Expired", value: numberText(state.expiredJobs.count), icon: "xmark.circle.fill", color: HDTheme.red)
            }
        }
        .premiumCard()
    }
}

struct DashboardStat: View {
    let title: String
    let value: Int
    let icon: String
    let color: Color

    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: icon)
                .font(.system(size: 13, weight: .bold))
                .foregroundStyle(color)
                .frame(width: 30, height: 30)
                .background(color.opacity(0.09))
                .clipShape(Circle())

            VStack(alignment: .leading, spacing: 1) {
                Text(numberText(value))
                    .font(.system(size: 20, weight: .black, design: .rounded))
                    .foregroundStyle(HDTheme.navy)
                Text(title)
                    .font(.caption2.weight(.bold))
                    .foregroundStyle(.secondary)
            }
            Spacer(minLength: 0)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 9)
        .background(Color.black.opacity(0.022))
        .clipShape(RoundedRectangle(cornerRadius: 13, style: .continuous))
    }
}

struct TrafficSummaryCard: View {
    @EnvironmentObject private var state: AppState

    private var periodLabel: String {
        switch state.trafficDays {
        case 1: return "24H"
        case 30: return "30D"
        default: return "7D"
        }
    }

    private var maxActivity: Int {
        max(
            state.traffic?.totals?.visitors ?? 0,
            state.traffic?.totals?.pageviews ?? 0,
            state.traffic?.conversions?.applyClicks ?? 0,
            state.traffic?.conversions?.resumeChecks ?? 0,
            1
        )
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                PremiumSectionTitle(
                    icon: "chart.line.uptrend.xyaxis",
                    title: "Website traffic",
                    subtitle: "Live GA4 snapshot",
                    color: HDTheme.cyan
                )

                Picker("Period", selection: Binding(
                    get: { state.trafficDays },
                    set: { days in Task { await state.loadTraffic(days: days) } }
                )) {
                    Text("24H").tag(1)
                    Text("7D").tag(7)
                    Text("30D").tag(30)
                }
                .pickerStyle(.segmented)
                .frame(width: 150)
            }

            HStack(spacing: 8) {
                PremiumMetricTile(title: "Live", value: numberText(state.traffic?.realtimeUsers), icon: "dot.radiowaves.left.and.right", color: HDTheme.green)
                PremiumMetricTile(title: "Users", value: numberText(state.traffic?.totals?.visitors), icon: "person.2.fill", color: HDTheme.blue)
                PremiumMetricTile(title: "Views", value: numberText(state.traffic?.totals?.pageviews), icon: "eye.fill", color: HDTheme.violet)
            }

            VStack(spacing: 9) {
                PremiumBarRow(title: "Users", value: state.traffic?.totals?.visitors ?? 0, maxValue: maxActivity, color: HDTheme.blue)
                PremiumBarRow(title: "Page views", value: state.traffic?.totals?.pageviews ?? 0, maxValue: maxActivity, color: HDTheme.violet)
                PremiumBarRow(title: "Apply clicks", value: state.traffic?.conversions?.applyClicks ?? 0, maxValue: maxActivity, color: HDTheme.green)
                PremiumBarRow(title: "Resume checks", value: state.traffic?.conversions?.resumeChecks ?? 0, maxValue: maxActivity, color: HDTheme.cyan)
            }

            if let top = state.traffic?.pages?.first {
                PremiumInfoBox(
                    icon: "flame.fill",
                    title: "Top page · \\(periodLabel)",
                    text: "\\(jobDisplayName(path: top.requestPath, jobs: state.jobs)) · \\(numberText(top.pageviews)) views",
                    color: HDTheme.amber
                )
            }
        }
        .premiumCard()
    }
}

struct TrafficMetric: View {
    let title: String
    let value: Int
    let icon: String
    let color: Color

    var body: some View {
        VStack(spacing: 5) {
            Image(systemName: icon)
                .font(.caption.weight(.bold))
                .foregroundStyle(color)
            Text(numberText(value))
                .font(.system(size: 21, weight: .black, design: .rounded))
                .foregroundStyle(HDTheme.navy)
            Text(title)
                .font(.caption2.weight(.bold))
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
    }
}

struct AnalyticsMiniMetric: View {
    let title: String
    let value: String
    let icon: String

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            Image(systemName: icon)
                .font(.caption2.weight(.bold))
                .foregroundStyle(HDTheme.blue)
            Text(value)
                .font(.subheadline.weight(.black))
                .foregroundStyle(HDTheme.navy)
                .lineLimit(1)
                .minimumScaleFactor(0.7)
            Text(title)
                .font(.system(size: 9, weight: .bold))
                .foregroundStyle(.secondary)
                .lineLimit(1)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(10)
        .background(HDTheme.blue.opacity(0.045))
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
    }
}

struct TrafficTrendCard: View {
    @EnvironmentObject private var state: AppState

    private var points: [TrafficResponse.TrendPoint] {
        state.traffic?.trend ?? []
    }

    private func compactDate(_ raw: String?) -> String {
        guard let raw, raw.count == 8 else { return raw ?? "" }
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyyMMdd"
        guard let date = formatter.date(from: raw) else { return raw }
        formatter.dateFormat = "d MMM"
        return formatter.string(from: date)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            AnalyticsSectionHeader(
                title: "Traffic trend",
                subtitle: "Users and page views over the selected period",
                icon: "chart.xyaxis.line"
            )

            if points.isEmpty {
                AnalyticsEmptyState(text: "Trend data will appear as GA4 accumulates daily traffic.")
            } else {
                Chart(points) { point in
                    LineMark(
                        x: .value("Date", compactDate(point.date)),
                        y: .value("Users", point.users ?? 0)
                    )
                    .foregroundStyle(HDTheme.blue)
                    .interpolationMethod(.catmullRom)

                    PointMark(
                        x: .value("Date", compactDate(point.date)),
                        y: .value("Users", point.users ?? 0)
                    )
                    .foregroundStyle(HDTheme.blue)

                    LineMark(
                        x: .value("Date", compactDate(point.date)),
                        y: .value("Views", point.pageviews ?? 0)
                    )
                    .foregroundStyle(.purple)
                    .interpolationMethod(.catmullRom)
                }
                .chartLegend(position: .bottom, alignment: .leading)
                .chartForegroundStyleScale([
                    "Users": HDTheme.blue,
                    "Views": Color.purple
                ])
                .frame(height: 190)
            }
        }
        .hdCard()
    }
}

struct AudienceAnalyticsCard: View {
    @EnvironmentObject private var state: AppState

    private var newUsers: Int { state.traffic?.totals?.newUsers ?? 0 }
    private var returningUsers: Int { state.traffic?.totals?.returningUsers ?? 0 }
    private var total: Int { max(1, newUsers + returningUsers) }

    private var slices: [AnalyticsSlice] {
        [
            AnalyticsSlice(name: "New", value: newUsers),
            AnalyticsSlice(name: "Returning", value: returningUsers)
        ].filter { $0.value > 0 }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 13) {
            AnalyticsSectionHeader(
                title: "Audience",
                subtitle: "New vs returning visitors",
                icon: "person.3.fill"
            )

            if slices.isEmpty {
                AnalyticsEmptyState(text: "Audience split is not available yet.")
            } else {
                HStack(spacing: 18) {
                    Chart(slices) { item in
                        SectorMark(
                            angle: .value("Users", item.value),
                            innerRadius: .ratio(0.62),
                            angularInset: 2
                        )
                        .foregroundStyle(by: .value("Audience", item.name))
                        .cornerRadius(4)
                    }
                    .chartLegend(.hidden)
                    .frame(width: 126, height: 126)

                    VStack(alignment: .leading, spacing: 12) {
                        AudienceLegendRow(
                            title: "New visitors",
                            value: newUsers,
                            percent: Double(newUsers) / Double(total) * 100,
                            color: HDTheme.blue
                        )
                        AudienceLegendRow(
                            title: "Returning",
                            value: returningUsers,
                            percent: Double(returningUsers) / Double(total) * 100,
                            color: .purple
                        )
                        Divider()
                        HStack {
                            Text("Avg. session")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            Spacer()
                            Text(durationText(state.traffic?.totals?.averageSessionDuration ?? 0))
                                .font(.caption.weight(.black))
                                .foregroundStyle(HDTheme.navy)
                        }
                    }
                    .frame(maxWidth: .infinity)
                }
            }

            if let devices = state.traffic?.realtime?.devices, !devices.isEmpty {
                Divider()
                Text("Live devices")
                    .font(.caption.weight(.black))
                    .foregroundStyle(HDTheme.navy)
                AnalyticsBarRows(
                    rows: devices.prefix(3).map { AnalyticsBarItem(name: ($0.deviceType ?? "Unknown").capitalized, value: $0.users ?? 0) }
                )
            }
        }
        .hdCard()
    }

    private func durationText(_ seconds: Double) -> String {
        let rounded = Int(seconds.rounded())
        if rounded < 60 { return "\(rounded)s" }
        return "\(rounded / 60)m \(rounded % 60)s"
    }
}

struct AcquisitionAnalyticsCard: View {
    @EnvironmentObject private var state: AppState

    private var channelItems: [AnalyticsBarItem] {
        (state.traffic?.channels ?? []).prefix(6).map {
            AnalyticsBarItem(name: $0.channel ?? "Other", value: $0.sessions ?? 0)
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 13) {
            AnalyticsSectionHeader(
                title: "Acquisition",
                subtitle: "Where sessions are coming from",
                icon: "arrow.triangle.branch"
            )

            if channelItems.isEmpty {
                AnalyticsEmptyState(text: "Acquisition channels will appear once GA4 has enough data.")
            } else {
                Chart(channelItems) { item in
                    BarMark(
                        x: .value("Sessions", item.value),
                        y: .value("Channel", item.name)
                    )
                    .foregroundStyle(HDTheme.blue.gradient)
                    .cornerRadius(5)
                }
                .chartLegend(.hidden)
                .frame(height: CGFloat(max(160, channelItems.count * 34)))
            }

            if let countries = state.traffic?.countries, !countries.isEmpty {
                Divider()
                Text("Top countries")
                    .font(.caption.weight(.black))
                    .foregroundStyle(HDTheme.navy)
                AnalyticsBarRows(
                    rows: countries.prefix(5).map { AnalyticsBarItem(name: $0.country ?? "Unknown", value: $0.visitors ?? 0) }
                )
            }
        }
        .hdCard()
    }
}

struct ConversionAnalyticsCard: View {
    @EnvironmentObject private var state: AppState

    private var items: [AnalyticsBarItem] {
        let c = state.traffic?.conversions
        return [
            AnalyticsBarItem(name: "Job views", value: c?.jobPageViews ?? 0),
            AnalyticsBarItem(name: "Resume checks", value: c?.resumeChecks ?? 0),
            AnalyticsBarItem(name: "Apply clicks", value: c?.applyClicks ?? 0),
            AnalyticsBarItem(name: "Apply users", value: c?.applyUsers ?? 0)
        ]
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 13) {
            AnalyticsSectionHeader(
                title: "Conversion funnel",
                subtitle: "How visitors move from job page to application",
                icon: "point.3.connected.trianglepath.dotted"
            )

            HStack(spacing: 8) {
                AnalyticsMiniMetric(
                    title: "Apply rate",
                    value: String(format: "%.1f%%", state.traffic?.conversions?.applyRate ?? 0),
                    icon: "cursorarrow.click.2"
                )
                AnalyticsMiniMetric(
                    title: "Resume users",
                    value: numberText(state.traffic?.conversions?.resumeUsers),
                    icon: "doc.text.magnifyingglass"
                )
                AnalyticsMiniMetric(
                    title: "Social",
                    value: numberText((state.traffic?.conversions?.socialClicks ?? 0) + (state.traffic?.conversions?.shares ?? 0)),
                    icon: "square.and.arrow.up.fill"
                )
            }

            Chart(items) { item in
                BarMark(
                    x: .value("Stage", item.name),
                    y: .value("Count", item.value)
                )
                .foregroundStyle(HDTheme.green.gradient)
                .cornerRadius(6)
            }
            .chartLegend(.hidden)
            .frame(height: 175)
        }
        .hdCard()
    }
}

struct TopContentAnalyticsCard: View {
    @EnvironmentObject private var state: AppState

    private var pages: [TrafficResponse.Page] {
        Array((state.traffic?.pages ?? []).prefix(5))
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 13) {
            AnalyticsSectionHeader(
                title: "Top content",
                subtitle: "Most-viewed pages in this period",
                icon: "flame.fill"
            )

            if pages.isEmpty {
                AnalyticsEmptyState(text: "Top pages will appear once traffic is recorded.")
            } else {
                VStack(spacing: 12) {
                    ForEach(Array(pages.enumerated()), id: \.element.id) { index, page in
                        HStack(spacing: 10) {
                            Text("\(index + 1)")
                                .font(.caption.weight(.black))
                                .foregroundStyle(HDTheme.blue)
                                .frame(width: 26, height: 26)
                                .background(HDTheme.blue.opacity(0.08))
                                .clipShape(Circle())

                            VStack(alignment: .leading, spacing: 2) {
                                Text(jobDisplayName(path: page.requestPath, jobs: state.jobs))
                                    .font(.caption.weight(.bold))
                                    .foregroundStyle(HDTheme.navy)
                                    .lineLimit(2)
                                Text(page.requestPath ?? "/")
                                    .font(.system(size: 9))
                                    .foregroundStyle(.secondary)
                                    .lineLimit(1)
                            }

                            Spacer()

                            Text(numberText(page.pageviews))
                                .font(.subheadline.weight(.black))
                                .foregroundStyle(HDTheme.navy)
                        }

                        if index < pages.count - 1 {
                            Divider()
                        }
                    }
                }
            }
        }
        .hdCard()
    }
}

struct AnalyticsSectionHeader: View {
    let title: String
    let subtitle: String
    let icon: String

    var body: some View {
        HStack(spacing: 11) {
            Image(systemName: icon)
                .font(.subheadline.weight(.bold))
                .foregroundStyle(HDTheme.blue)
                .frame(width: 34, height: 34)
                .background(HDTheme.blue.opacity(0.08))
                .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))

            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.headline.weight(.black))
                    .foregroundStyle(HDTheme.navy)
                Text(subtitle)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }
}

struct AnalyticsSlice: Identifiable {
    let name: String
    let value: Int
    var id: String { name }
}

struct AnalyticsBarItem: Identifiable {
    let name: String
    let value: Int
    var id: String { name }
}

struct AnalyticsBarRows: View {
    let rows: [AnalyticsBarItem]

    private var maxValue: Int {
        max(1, rows.map(\.value).max() ?? 1)
    }

    var body: some View {
        VStack(spacing: 10) {
            ForEach(rows) { item in
                VStack(spacing: 5) {
                    HStack {
                        Text(item.name)
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(HDTheme.navy)
                            .lineLimit(1)
                        Spacer()
                        Text(numberText(item.value))
                            .font(.caption.weight(.black))
                            .foregroundStyle(HDTheme.navy)
                    }

                    GeometryReader { geo in
                        ZStack(alignment: .leading) {
                            Capsule()
                                .fill(Color.black.opacity(0.055))
                            Capsule()
                                .fill(HDTheme.blue.opacity(0.75))
                                .frame(width: geo.size.width * CGFloat(item.value) / CGFloat(maxValue))
                        }
                    }
                    .frame(height: 7)
                }
            }
        }
    }
}

struct AudienceLegendRow: View {
    let title: String
    let value: Int
    let percent: Double
    let color: Color

    var body: some View {
        HStack(spacing: 9) {
            Circle()
                .fill(color)
                .frame(width: 9, height: 9)
            VStack(alignment: .leading, spacing: 1) {
                Text(title)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(HDTheme.navy)
                Text(String(format: "%.1f%%", percent))
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Text(numberText(value))
                .font(.subheadline.weight(.black))
                .foregroundStyle(HDTheme.navy)
        }
    }
}

struct AnalyticsEmptyState: View {
    let text: String

    var body: some View {
        HStack(spacing: 9) {
            Image(systemName: "chart.bar.xaxis")
                .foregroundStyle(.secondary)
            Text(text)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.black.opacity(0.025))
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
    }
}

struct SmallMetric: View {
    let title: String
    let value: Int
    let color: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            Text(numberText(value))
                .font(.title3.weight(.black))
                .foregroundStyle(HDTheme.navy)
            Text(title)
                .font(.caption2.weight(.bold))
                .foregroundStyle(color)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(11)
        .background(color.opacity(0.08))
        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
    }
}


struct AutomationHealthCard: View {
    @EnvironmentObject private var state: AppState
    @State private var showLastRun = false

    private func outcomeColor(_ outcome: String?) -> Color {
        switch outcome {
        case "published": return HDTheme.green
        case "partial", "no_publish": return HDTheme.amber
        case "error": return HDTheme.red
        case "scheduled": return HDTheme.blue
        default: return HDTheme.blue
        }
    }

    private func outcomeLabel(_ outcome: String?) -> String {
        if outcome == "scheduled" { return "Ready" }
        return outcome?.replacingOccurrences(of: "_", with: " ").capitalized ?? "Scheduled"
    }

    private func nextRunText(_ slot: AutomationHealth.Slot) -> String {
        let iso = ISO8601DateFormatter()
        iso.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        var stored = slot.nextRunAt.flatMap { iso.date(from: $0) }
        if stored == nil {
            iso.formatOptions = [.withInternetDateTime]
            stored = slot.nextRunAt.flatMap { iso.date(from: $0) }
        }

        if let stored, stored > Date() {
            return formatAdminDate(slot.nextRunAt)
        }

        let zone = TimeZone(identifier: slot.timezone ?? "Asia/Kolkata") ?? .current
        let parts = slot.time.split(separator: ":")
        let hour = parts.first.flatMap { Int($0) } ?? 9
        let minute = parts.dropFirst().first.flatMap { Int($0) } ?? 0
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = zone
        var components = calendar.dateComponents([.year, .month, .day], from: Date())
        components.hour = hour
        components.minute = minute
        components.second = 0
        var next = calendar.date(from: components) ?? Date()
        if next <= Date() {
            next = calendar.date(byAdding: .day, value: 1, to: next) ?? next
        }

        let display = DateFormatter()
        display.locale = Locale(identifier: "en_IN")
        display.timeZone = zone
        display.dateFormat = "dd MMM, h:mm a"
        return display.string(from: next) + " IST"
    }

    var body: some View {
        Group {
            if let slot = state.automationHealth?.slots.first(where: { $0.enabled }) {
                VStack(spacing: 0) {
                    ZStack(alignment: .bottomLeading) {
                        LinearGradient(
                            colors: [HDTheme.navy, HDTheme.blue],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                        .frame(height: 142)

                        Circle()
                            .fill(Color.white.opacity(0.09))
                            .frame(width: 130, height: 130)
                            .offset(x: 245, y: -48)

                        VStack(alignment: .leading, spacing: 10) {
                            HStack {
                                HStack(spacing: 8) {
                                    Image(systemName: "bolt.fill")
                                    Text("DAILY PUBLISHING")
                                        .tracking(1)
                                }
                                .font(.caption2.weight(.black))
                                .foregroundStyle(.white.opacity(0.78))

                                Spacer()

                                StatusPill(
                                    text: outcomeLabel(slot.outcome),
                                    color: outcomeColor(slot.outcome)
                                )
                            }

                            Text("9:00 AM Batch")
                                .font(.system(size: 25, weight: .black, design: .rounded))
                                .foregroundStyle(.white)

                            HStack(spacing: 8) {
                                Label(slot.target ?? "9–10 verified jobs/day", systemImage: "target")
                                Spacer()
                                Label(nextRunText(slot), systemImage: "clock.fill")
                            }
                            .font(.caption.weight(.bold))
                            .foregroundStyle(.white.opacity(0.9))
                        }
                        .padding(18)
                    }

                    VStack(alignment: .leading, spacing: 15) {
                        VStack(alignment: .leading, spacing: 9) {
                            Text("Today’s publishing mix")
                                .font(.subheadline.weight(.black))
                                .foregroundStyle(HDTheme.navy)

                            if let mix = slot.mix, !mix.isEmpty {
                                LazyVGrid(
                                    columns: [GridItem(.adaptive(minimum: 130), spacing: 8)],
                                    alignment: .leading,
                                    spacing: 8
                                ) {
                                    ForEach(Array(mix.enumerated()), id: \.offset) { index, item in
                                        HStack(spacing: 6) {
                                            Image(systemName: publishingIcon(index))
                                                .font(.caption2.weight(.bold))
                                                .foregroundStyle(HDTheme.blue)
                                            Text(item)
                                                .font(.caption2.weight(.bold))
                                                .foregroundStyle(HDTheme.navy)
                                                .lineLimit(1)
                                        }
                                        .padding(.horizontal, 10)
                                        .padding(.vertical, 8)
                                        .background(HDTheme.blue.opacity(0.07))
                                        .clipShape(Capsule())
                                    }
                                }
                            }
                        }

                        HStack(spacing: 5) {
                            PublishingStep(icon: "magnifyingglass", title: "Find")
                            PipelineArrow()
                            PublishingStep(icon: "checkmark.shield.fill", title: "Verify")
                            PipelineArrow()
                            PublishingStep(icon: "arrow.up.circle.fill", title: "Publish")
                            PipelineArrow()
                            PublishingStep(icon: "paperplane.fill", title: "Telegram")
                        }

                        if let delivery = slot.delivery, !delivery.isEmpty {
                            Text(delivery)
                                .font(.caption2.weight(.semibold))
                                .foregroundStyle(.secondary)
                                .lineLimit(2)
                        }

                        Button {
                            withAnimation(.snappy(duration: 0.28)) {
                                showLastRun.toggle()
                            }
                        } label: {
                            HStack {
                                Image(systemName: showLastRun ? "chart.bar.fill" : "clock.arrow.circlepath")
                                    .foregroundStyle(HDTheme.blue)
                                VStack(alignment: .leading, spacing: 1) {
                                    Text(showLastRun ? "Hide last run" : "Show last run")
                                        .font(.subheadline.weight(.bold))
                                        .foregroundStyle(HDTheme.navy)
                                    if let last = slot.lastRunAt {
                                        Text("Previous: \(formatAdminDate(last))")
                                            .font(.caption2)
                                            .foregroundStyle(.secondary)
                                    }
                                }
                                Spacer()
                                Image(systemName: "chevron.down")
                                    .font(.caption.weight(.bold))
                                    .foregroundStyle(HDTheme.blue)
                                    .rotationEffect(.degrees(showLastRun ? 180 : 0))
                            }
                            .padding(12)
                            .background(HDTheme.blue.opacity(0.055))
                            .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                        }
                        .buttonStyle(.plain)

                        if showLastRun {
                            VStack(alignment: .leading, spacing: 9) {
                                HStack {
                                    Label("Last run result", systemImage: "waveform.path.ecg")
                                        .font(.caption.weight(.black))
                                        .foregroundStyle(HDTheme.navy)
                                    Spacer()
                                    StatusPill(
                                        text: outcomeLabel(slot.outcome),
                                        color: outcomeColor(slot.outcome)
                                    )
                                }

                                if let detail = slot.detail, !detail.isEmpty {
                                    Text(detail)
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                        .fixedSize(horizontal: false, vertical: true)
                                } else {
                                    Text("No run details are available yet.")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                            }
                            .padding(13)
                            .background(outcomeColor(slot.outcome).opacity(0.055))
                            .overlay {
                                RoundedRectangle(cornerRadius: 14, style: .continuous)
                                    .stroke(outcomeColor(slot.outcome).opacity(0.16))
                            }
                            .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                            .transition(.opacity.combined(with: .move(edge: .top)))
                        }
                    }
                    .padding(16)
                    .background(Color.white)
                }
                .clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous))
                .overlay {
                    RoundedRectangle(cornerRadius: 22, style: .continuous)
                        .stroke(Color.black.opacity(0.06))
                }
                .shadow(color: Color.black.opacity(0.045), radius: 12, x: 0, y: 5)
            } else {
                VStack(alignment: .leading, spacing: 8) {
                    Label("Publishing automation", systemImage: "bolt.slash")
                        .font(.headline.weight(.black))
                    Text("Refresh to load the active daily publishing schedule.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .hdCard()
            }
        }
    }

    private func publishingIcon(_ index: Int) -> String {
        switch index {
        case 0: return "laptopcomputer"
        case 1: return "person.crop.circle.badge.plus"
        case 2: return "briefcase.fill"
        case 3: return "building.columns.fill"
        default: return "figure.walk"
        }
    }
}

struct PublishingStep: View {
    let icon: String
    let title: String

    var body: some View {
        VStack(spacing: 5) {
            Image(systemName: icon)
                .font(.caption.weight(.bold))
                .foregroundStyle(HDTheme.blue)
                .frame(width: 28, height: 28)
                .background(HDTheme.blue.opacity(0.08))
                .clipShape(Circle())
            Text(title)
                .font(.system(size: 9, weight: .bold))
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
    }
}

struct PipelineArrow: View {
    var body: some View {
        Image(systemName: "chevron.right")
            .font(.system(size: 9, weight: .black))
            .foregroundStyle(.tertiary)
    }
}

enum JobListFilter: String, CaseIterable, Identifiable {
    case all = "All"
    case active = "Active"
    case expired = "Expired"
    var id: String { rawValue }
}

struct JobsView: View {
    @EnvironmentObject private var state: AppState
    @State private var search = ""
    @State private var filter: JobListFilter = .all

    private var filteredJobs: [Job] {
        state.jobs.filter { job in
            let matchesFilter: Bool
            switch filter {
            case .all: matchesFilter = true
            case .active: matchesFilter = job.isActive
            case .expired: matchesFilter = job.isExpired
            }

            guard matchesFilter else { return false }
            guard !search.isEmpty else { return true }
            let haystack = [job.company, job.role, job.loc, job.cat].compactMap { $0 }.joined(separator: " ").lowercased()
            return haystack.contains(search.lowercased())
        }
    }

    var body: some View {
        NavigationStack {
            ZStack {
                HDTheme.background.ignoresSafeArea()

                ScrollView {
                    VStack(spacing: 13) {
                        AdminHeader(
                            title: "Jobs",
                            subtitle: "\\(state.jobs.count) published openings",
                            trailingSystemImage: "arrow.clockwise"
                        ) {
                            Task { await state.refreshJobs() }
                        }

                        HStack(spacing: 8) {
                            PremiumMetricTile(title: "Active", value: numberText(state.activeJobs.count), icon: "checkmark.circle.fill", color: HDTheme.green)
                            PremiumMetricTile(title: "Freshers", value: numberText(state.fresherJobs.count), icon: "person.fill", color: HDTheme.violet)
                            PremiumMetricTile(title: "Expired", value: numberText(state.expiredJobs.count), icon: "xmark.circle.fill", color: HDTheme.red)
                        }

                        HStack(spacing: 10) {
                            Image(systemName: "magnifyingglass")
                                .foregroundStyle(HDTheme.blue)
                            TextField("Search company, role or location", text: $search)
                                .textInputAutocapitalization(.never)
                                .font(.subheadline)
                        }
                        .padding(.horizontal, 13)
                        .frame(height: 46)
                        .background(.white)
                        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                        .overlay {
                            RoundedRectangle(cornerRadius: 14, style: .continuous)
                                .stroke(HDTheme.blue.opacity(0.10))
                        }
                        .shadow(color: HDTheme.navy.opacity(0.035), radius: 8, y: 3)

                        Picker("Status", selection: $filter) {
                            ForEach(JobListFilter.allCases) { item in
                                Text("\\(item.rawValue) \\(count(for: item))").tag(item)
                            }
                        }
                        .pickerStyle(.segmented)

                        if filteredJobs.isEmpty {
                            EmptyState(icon: "briefcase", title: "No jobs found", message: "Try changing your search or status filter.")
                                .premiumCard()
                        } else {
                            LazyVStack(spacing: 9) {
                                ForEach(filteredJobs) { job in
                                    JobRow(job: job)
                                }
                            }
                        }
                    }
                    .padding(16)
                    .padding(.bottom, 18)
                }
                .refreshable { await state.refreshJobs() }
            }
            .toolbar(.hidden, for: .navigationBar)
        }
    }

    private func count(for filter: JobListFilter) -> Int {
        switch filter {
        case .all: return state.jobs.count
        case .active: return state.activeJobs.count
        case .expired: return state.expiredJobs.count
        }
    }
}

struct JobRow: View {
    let job: Job

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            CompanyLogoView(job: job, size: 50)

            VStack(alignment: .leading, spacing: 7) {
                HStack(alignment: .top, spacing: 8) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(job.company ?? "Company")
                            .font(.headline.weight(.black))
                            .foregroundStyle(HDTheme.navy)
                            .lineLimit(1)

                        Text(job.role ?? "Job Opening")
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(.secondary)
                            .lineLimit(2)
                    }

                    Spacer(minLength: 5)

                    StatusPill(
                        text: job.isExpired ? "Expired" : "Active",
                        color: job.isExpired ? HDTheme.red : HDTheme.green,
                        icon: job.isExpired ? "xmark" : "checkmark"
                    )
                }

                HStack(spacing: 6) {
                    PremiumMetaChip(text: job.loc ?? "Location", icon: "mappin.and.ellipse", color: HDTheme.blue)
                    PremiumMetaChip(text: job.expType?.capitalized ?? "Job", icon: "person.fill", color: HDTheme.violet)
                    if let mode = job.workMode, !mode.isEmpty {
                        PremiumMetaChip(text: mode, icon: "laptopcomputer", color: HDTheme.cyan)
                    }
                }
                .lineLimit(1)

                HStack {
                    if let salary = job.salary, !salary.isEmpty {
                        Label(salary, systemImage: "indianrupeesign.circle")
                            .font(.caption2.weight(.semibold))
                            .foregroundStyle(.secondary)
                            .lineLimit(1)
                    }

                    Spacer()

                    if let site = job.siteURL {
                        Link(destination: site) {
                            Image(systemName: "eye")
                        }
                    }

                    if let official = job.officialURL {
                        Link(destination: official) {
                            Label("Official", systemImage: "arrow.up.right")
                        }
                    }
                }
                .font(.caption.weight(.bold))
                .foregroundStyle(HDTheme.blue)
            }
        }
        .premiumCard(13)
    }
}

struct ParsedAdminLink: Identifiable {
    let lineIndex: Int
    let raw: String
    let url: URL?
    let duplicate: Bool

    var id: String { "\(lineIndex)-\(raw)" }
    var valid: Bool { url?.scheme == "https" && !(url?.host?.isEmpty ?? true) }
    var domain: String { url?.host?.replacingOccurrences(of: "www.", with: "") ?? "Invalid URL" }
    var path: String {
        guard let url else { return raw }
        let query = url.query.map { "?\($0)" } ?? ""
        return url.path + query
    }
}

struct EditSelection: Identifiable {
    let id: Int
}


struct PublishHeroCard: View {
    let readyCount: Int
    let draftCount: Int
    let selectedCount: Int
    let isGenerating: Bool

    var body: some View {
        ZStack {
            LinearGradient(
                colors: [HDTheme.navy, Color(red: 0.18, green: 0.12, blue: 0.50), HDTheme.blue],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )

            Circle()
                .fill(Color.white.opacity(0.08))
                .frame(width: 150, height: 150)
                .offset(x: 150, y: -60)

            VStack(alignment: .leading, spacing: 15) {
                HStack {
                    VStack(alignment: .leading, spacing: 3) {
                        Text("PUBLISHING WORKSPACE")
                            .font(.system(size: 10, weight: .black))
                            .tracking(1.1)
                            .foregroundStyle(.white.opacity(0.72))
                        Text("Official link → live job")
                            .font(.system(size: 24, weight: .black, design: .rounded))
                            .foregroundStyle(.white)
                    }
                    Spacer()
                    Image(systemName: "wand.and.stars")
                        .font(.system(size: 23, weight: .bold))
                        .foregroundStyle(.white.opacity(0.92))
                }

                HStack(spacing: 4) {
                    PublishWorkflowStep(number: "1", title: "Links", icon: "link", active: readyCount > 0)
                    Image(systemName: "chevron.right").font(.caption2.weight(.black)).foregroundStyle(.white.opacity(0.35))
                    PublishWorkflowStep(number: "2", title: "Generate", icon: "sparkles", active: isGenerating || draftCount > 0)
                    Image(systemName: "chevron.right").font(.caption2.weight(.black)).foregroundStyle(.white.opacity(0.35))
                    PublishWorkflowStep(number: "3", title: "Review", icon: "checklist", active: draftCount > 0)
                    Image(systemName: "chevron.right").font(.caption2.weight(.black)).foregroundStyle(.white.opacity(0.35))
                    PublishWorkflowStep(number: "4", title: "Publish", icon: "paperplane.fill", active: selectedCount > 0)
                }
            }
            .padding(18)
        }
        .frame(height: 170)
        .clipShape(RoundedRectangle(cornerRadius: 24, style: .continuous))
        .shadow(color: HDTheme.navy.opacity(0.14), radius: 16, x: 0, y: 8)
    }
}

struct PublishView: View {
    @EnvironmentObject private var state: AppState
    @State private var rawLinks = ""
    @State private var drafts: [Job] = []
    @State private var selectedIDs: Set<String> = []
    @State private var isGenerating = false
    @State private var processed = 0
    @State private var extractionIssues: [String] = []
    @State private var editSelection: EditSelection?
    @State private var showPublishConfirmation = false

    private var parsedLinks: [ParsedAdminLink] {
        let lines = rawLinks
            .split(whereSeparator: \.isNewline)
            .map { String($0).trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }

        var seen = Set<String>()
        return lines.enumerated().map { index, raw in
            let url = URL(string: raw)
            let normalized = url?.absoluteString.lowercased().trimmingCharacters(in: CharacterSet(charactersIn: "/")) ?? raw.lowercased()
            let duplicate = seen.contains(normalized)
            if url != nil && !duplicate { seen.insert(normalized) }
            return ParsedAdminLink(lineIndex: index, raw: raw, url: url, duplicate: duplicate)
        }
    }

    private var readyLinks: [ParsedAdminLink] {
        parsedLinks.filter { $0.valid && !$0.duplicate }
    }

    private var selectedDrafts: [Job] {
        drafts.filter { selectedIDs.contains($0.id) }
    }

    var body: some View {
        NavigationStack {
            ZStack {
                HDTheme.background.ignoresSafeArea()

                ScrollView {
                    VStack(spacing: 14) {
                        AdminHeader(title: "Publish", subtitle: "Create verified job posts")

                        PublishHeroCard(
                            readyCount: readyLinks.count,
                            draftCount: drafts.count,
                            selectedCount: selectedDrafts.count,
                            isGenerating: isGenerating
                        )

                        VStack(alignment: .leading, spacing: 13) {
                            HStack {
                                PremiumSectionTitle(
                                    icon: "link.badge.plus",
                                    title: "Official job links",
                                    subtitle: "Paste up to 20 employer URLs",
                                    color: HDTheme.blue
                                )
                                StatusPill(
                                    text: "\\(readyLinks.count) ready",
                                    color: readyLinks.isEmpty ? Color.gray : HDTheme.green,
                                    icon: readyLinks.isEmpty ? "link" : "checkmark.circle.fill"
                                )
                            }

                            PremiumInfoBox(
                                icon: "checkmark.shield.fill",
                                title: "Official sources only",
                                text: "Use employer careers pages or official ATS links. Each link is extracted, validated and reviewed before publishing.",
                                color: HDTheme.green
                            )

                            ZStack(alignment: .topLeading) {
                                if rawLinks.isEmpty {
                                    Text("https://company.com/careers/job/123\nhttps://jobs.company.com/opening/456")
                                        .font(.caption)
                                        .foregroundStyle(.tertiary)
                                        .padding(.horizontal, 14)
                                        .padding(.vertical, 16)
                                        .allowsHitTesting(false)
                                }

                                TextEditor(text: $rawLinks)
                                    .font(.caption)
                                    .frame(minHeight: 118)
                                    .padding(8)
                                    .scrollContentBackground(.hidden)
                                    .background(Color(.secondarySystemBackground))
                                    .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                            }

                            if !parsedLinks.isEmpty {
                                VStack(spacing: 8) {
                                    ForEach(parsedLinks) { item in
                                        LinkPreviewRow(item: item) {
                                            removeLink(at: item.lineIndex)
                                        }
                                    }
                                }
                            }

                            if isGenerating {
                                VStack(spacing: 7) {
                                    HStack {
                                        Text("Extracting job details")
                                            .font(.caption.weight(.bold))
                                        Spacer()
                                        Text("\\(processed)/\\(readyLinks.count)")
                                            .font(.caption.weight(.black))
                                    }
                                    ProgressView(value: Double(processed), total: Double(max(readyLinks.count, 1)))
                                        .tint(HDTheme.blue)
                                }
                                .padding(11)
                                .background(HDTheme.blue.opacity(0.05))
                                .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                            }

                            Button {
                                Task { await generateJobs() }
                            } label: {
                                HStack(spacing: 8) {
                                    if isGenerating {
                                        ProgressView().tint(.white)
                                    } else {
                                        Image(systemName: "sparkles")
                                    }
                                    Text(isGenerating ? "Generating…" : "Generate \\(readyLinks.count) job\\(readyLinks.count == 1 ? "" : "s")")
                                        .font(.subheadline.weight(.black))
                                }
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 14)
                            }
                            .buttonStyle(.plain)
                            .foregroundStyle(.white)
                            .background(
                                LinearGradient(
                                    colors: readyLinks.isEmpty || isGenerating ? [Color.gray, Color.gray] : [HDTheme.navy, HDTheme.blue],
                                    startPoint: .leading,
                                    endPoint: .trailing
                                )
                            )
                            .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                            .disabled(readyLinks.isEmpty || isGenerating)
                        }
                        .premiumCard()

                        if !extractionIssues.isEmpty {
                            VStack(alignment: .leading, spacing: 9) {
                                PremiumSectionTitle(
                                    icon: "exclamationmark.triangle.fill",
                                    title: "Needs attention",
                                    subtitle: "\\(extractionIssues.count) extraction issue\\(extractionIssues.count == 1 ? "" : "s")",
                                    color: HDTheme.amber
                                )
                                ForEach(extractionIssues, id: \.self) { issue in
                                    PremiumInfoBox(
                                        icon: "exclamationmark.circle",
                                        title: "Could not extract",
                                        text: issue,
                                        color: HDTheme.amber
                                    )
                                }
                            }
                            .premiumCard()
                        }

                        if !drafts.isEmpty {
                            VStack(alignment: .leading, spacing: 12) {
                                HStack {
                                    PremiumSectionTitle(
                                        icon: "doc.text.magnifyingglass",
                                        title: "Generated preview",
                                        subtitle: "Review content before it goes live",
                                        color: HDTheme.violet
                                    )
                                    StatusPill(text: "\\(selectedDrafts.count) selected", color: HDTheme.violet)
                                }

                                ForEach(Array(drafts.enumerated()), id: \.element.id) { index, job in
                                    DraftJobRow(
                                        job: job,
                                        selected: selectedIDs.contains(job.id),
                                        toggle: {
                                            if selectedIDs.contains(job.id) {
                                                selectedIDs.remove(job.id)
                                            } else {
                                                selectedIDs.insert(job.id)
                                            }
                                        },
                                        edit: { editSelection = EditSelection(id: index) }
                                    )
                                }

                                PremiumInfoBox(
                                    icon: "arrow.triangle.branch",
                                    title: "What happens next",
                                    text: "Selected jobs run through validation, website generation, deployment and the existing Telegram publishing workflow.",
                                    color: HDTheme.cyan
                                )

                                Button {
                                    showPublishConfirmation = true
                                } label: {
                                    Label(
                                        "Publish \\(selectedDrafts.count) selected",
                                        systemImage: "paperplane.fill"
                                    )
                                    .font(.subheadline.weight(.black))
                                    .frame(maxWidth: .infinity)
                                    .padding(.vertical, 14)
                                }
                                .buttonStyle(.plain)
                                .foregroundStyle(.white)
                                .background(
                                    LinearGradient(
                                        colors: selectedDrafts.isEmpty ? [Color.gray, Color.gray] : [HDTheme.green, Color(red: 0.02, green: 0.46, blue: 0.35)],
                                        startPoint: .leading,
                                        endPoint: .trailing
                                    )
                                )
                                .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                                .disabled(selectedDrafts.isEmpty || state.isBusy)
                            }
                            .premiumCard()
                        }
                    }
                    .padding(16)
                    .padding(.bottom, 18)
                }
            }
            .toolbar(.hidden, for: .navigationBar)
            .sheet(item: $editSelection) { selection in
                if drafts.indices.contains(selection.id) {
                    JobEditSheet(job: Binding(
                        get: { drafts[selection.id] },
                        set: { drafts[selection.id] = $0 }
                    ))
                }
            }
            .confirmationDialog(
                "Publish selected jobs?",
                isPresented: $showPublishConfirmation,
                titleVisibility: .visible
            ) {
                Button("Publish \\(selectedDrafts.count) jobs") {
                    Task { await publishSelected() }
                }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("The existing HD Careers validation, generation, deployment and Telegram workflow will run.")
            }
        }
    }

    private func removeLink(at index: Int) {
        var lines = rawLinks
            .split(whereSeparator: \.isNewline)
            .map(String.init)
            .filter { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }

        guard lines.indices.contains(index) else { return }
        lines.remove(at: index)
        rawLinks = lines.joined(separator: "\n")
    }

    private func generateJobs() async {
        let links = readyLinks
        guard !links.isEmpty else { return }
        guard links.count <= 20 else {
            state.alertMessage = "Maximum 20 job links per batch."
            return
        }

        isGenerating = true
        processed = 0
        extractionIssues = []
        drafts = []
        selectedIDs = []

        var generated: [(Int, Job)] = []
        var issues: [String] = []

        for start in stride(from: 0, to: links.count, by: 3) {
            let end = min(start + 3, links.count)
            let batch = Array(links[start..<end])

            await withTaskGroup(of: (Int, Job?, String?).self) { group in
                for (offset, link) in batch.enumerated() {
                    let index = start + offset
                    group.addTask {
                        do {
                            let job = try await APIClient.shared.extractJob(url: link.raw)
                            return (index, job, nil)
                        } catch {
                            return (index, nil, "\\(link.domain): \\(error.localizedDescription)")
                        }
                    }
                }

                for await result in group {
                    processed += 1
                    if let job = result.1 {
                        generated.append((result.0, job))
                    }
                    if let issue = result.2 {
                        issues.append(issue)
                    }
                }
            }
        }

        drafts = generated.sorted { $0.0 < $1.0 }.map(\.1)
        selectedIDs = Set(drafts.map(\.id))
        extractionIssues = issues
        isGenerating = false
    }

    private func publishSelected() async {
        let jobs = selectedDrafts
        guard !jobs.isEmpty else { return }

        state.isBusy = true
        defer { state.isBusy = false }

        do {
            let response = try await state.api.publish(jobs: jobs)
            state.alertMessage = response.message ?? "Production deployment started."
            rawLinks = ""
            drafts = []
            selectedIDs = []
            extractionIssues = []
            try? await Task.sleep(for: .seconds(2))
            await state.refreshJobs()
        } catch {
            state.alertMessage = error.localizedDescription
        }
    }
}

struct LinkPreviewRow: View {
    let item: ParsedAdminLink
    let remove: () -> Void

    private var color: Color {
        if !item.valid { return HDTheme.red }
        if item.duplicate { return HDTheme.amber }
        return HDTheme.green
    }

    private var status: String {
        if !item.valid { return "Invalid" }
        if item.duplicate { return "Duplicate" }
        return "Verified"
    }

    var body: some View {
        HStack(alignment: .center, spacing: 11) {
            Image(systemName: item.valid ? "link.circle.fill" : "exclamationmark.triangle.fill")
                .font(.system(size: 16, weight: .bold))
                .foregroundStyle(color)
                .frame(width: 38, height: 38)
                .background(color.opacity(0.09))
                .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))

            VStack(alignment: .leading, spacing: 3) {
                HStack(spacing: 6) {
                    Text(item.domain)
                        .font(.caption.weight(.black))
                        .foregroundStyle(HDTheme.navy)
                        .lineLimit(1)
                    StatusPill(text: status, color: color)
                }

                Text(item.path)
                    .font(.system(size: 9.5))
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }

            Spacer(minLength: 4)

            if let url = item.url, item.valid {
                Link(destination: url) {
                    Image(systemName: "arrow.up.right")
                        .frame(width: 30, height: 30)
                        .background(HDTheme.blue.opacity(0.08))
                        .clipShape(RoundedRectangle(cornerRadius: 9, style: .continuous))
                }
            }

            Button(action: remove) {
                Image(systemName: "xmark")
                    .frame(width: 30, height: 30)
                    .background(Color.black.opacity(0.035))
                    .clipShape(RoundedRectangle(cornerRadius: 9, style: .continuous))
            }
            .buttonStyle(.plain)
            .foregroundStyle(.secondary)
        }
        .padding(10)
        .background(Color.white.opacity(0.78))
        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .stroke(color.opacity(0.14))
        }
    }
}

struct DraftJobRow: View {
    let job: Job
    let selected: Bool
    let toggle: () -> Void
    let edit: () -> Void

    var body: some View {
        HStack(alignment: .top, spacing: 11) {
            Button(action: toggle) {
                Image(systemName: selected ? "checkmark.circle.fill" : "circle")
                    .foregroundStyle(selected ? HDTheme.green : .secondary)
                    .font(.title3)
            }
            .buttonStyle(.plain)

            CompanyLogoView(job: job, size: 46)

            VStack(alignment: .leading, spacing: 6) {
                Text(job.company ?? "Company")
                    .font(.subheadline.weight(.black))
                    .foregroundStyle(HDTheme.navy)

                Text(job.role ?? "Job Opening")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)
                    .lineLimit(2)

                HStack(spacing: 6) {
                    PremiumMetaChip(text: job.cat?.capitalized ?? "Job", icon: "briefcase.fill", color: HDTheme.violet)
                    PremiumMetaChip(text: job.loc ?? "Location", icon: "mappin", color: HDTheme.blue)
                }
                .lineLimit(1)
            }

            Spacer(minLength: 5)

            Button(action: edit) {
                Image(systemName: "slider.horizontal.3")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(HDTheme.blue)
                    .frame(width: 34, height: 34)
                    .background(HDTheme.blue.opacity(0.08))
                    .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
            }
            .buttonStyle(.plain)
        }
        .padding(12)
        .background(selected ? HDTheme.green.opacity(0.035) : Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 15, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 15, style: .continuous)
                .stroke(selected ? HDTheme.green.opacity(0.18) : Color.black.opacity(0.045))
        }
    }
}

struct JobEditSheet: View {
    @Environment(\.dismiss) private var dismiss
    @Binding var job: Job

    private func binding(_ keyPath: WritableKeyPath<Job, String?>) -> Binding<String> {
        Binding(
            get: { job[keyPath: keyPath] ?? "" },
            set: { job[keyPath: keyPath] = $0 }
        )
    }

    private func listBinding(_ keyPath: WritableKeyPath<Job, [String]?>, commaSeparated: Bool = false) -> Binding<String> {
        Binding(
            get: {
                let values = job[keyPath: keyPath] ?? []
                return values.joined(separator: commaSeparated ? ", " : "\n")
            },
            set: { raw in
                let values: [String]
                if commaSeparated {
                    values = raw.split(separator: ",").map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }.filter { !$0.isEmpty }
                } else {
                    values = raw.components(separatedBy: .newlines).map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }.filter { !$0.isEmpty }
                }
                job[keyPath: keyPath] = values
            }
        )
    }

    var body: some View {
        NavigationStack {
            ZStack {
                HDTheme.background.ignoresSafeArea()

                ScrollView {
                    VStack(spacing: 13) {
                        HStack(spacing: 12) {
                            CompanyLogoView(job: job, size: 52)
                            VStack(alignment: .leading, spacing: 3) {
                                Text(job.company ?? "Company")
                                    .font(.headline.weight(.black))
                                    .foregroundStyle(HDTheme.navy)
                                Text(job.role ?? "Job Opening")
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.secondary)
                                    .lineLimit(2)
                            }
                            Spacer()
                        }
                        .premiumCard()

                        VStack(alignment: .leading, spacing: 11) {
                            PremiumSectionTitle(icon: "briefcase.fill", title: "Job basics", subtitle: "Candidate-facing summary")
                            PremiumField(title: "Company", icon: "building.2", text: binding(\.company))
                            PremiumField(title: "Role", icon: "person.crop.rectangle", text: binding(\.role))
                            PremiumField(title: "Location", icon: "mappin.and.ellipse", text: binding(\.loc))
                            PremiumField(title: "Experience", icon: "clock", text: binding(\.expYears))
                            PremiumField(title: "Batch / Qualification", icon: "graduationcap", text: binding(\.batch))
                            PremiumField(title: "Salary", icon: "indianrupeesign.circle", text: binding(\.salary))
                            PremiumField(title: "Work mode", icon: "laptopcomputer", text: binding(\.workMode))
                        }
                        .premiumCard()

                        VStack(alignment: .leading, spacing: 11) {
                            PremiumSectionTitle(icon: "checkmark.seal.fill", title: "Official source", subtitle: "Verification and application metadata", color: HDTheme.green)
                            PremiumField(title: "Official apply URL", icon: "link", text: binding(\.apply))
                            PremiumField(title: "Source name", icon: "building.columns", text: binding(\.sourceName))
                            PremiumField(title: "Verified date", icon: "calendar.badge.checkmark", text: binding(\.verifiedDate))
                            PremiumField(title: "Closing date", icon: "calendar.badge.exclamationmark", text: binding(\.closingAt))
                            PremiumField(title: "Job / Requisition ID", icon: "number", text: binding(\.externalJobId))
                            PremiumField(title: "Careers favicon URL", icon: "photo", text: binding(\.careerIconUrl))
                            PremiumField(title: "Full logo URL", icon: "photo.stack", text: binding(\.logoUrl))
                        }
                        .premiumCard()

                        VStack(alignment: .leading, spacing: 11) {
                            PremiumSectionTitle(icon: "building.2.crop.circle.fill", title: "Company details", subtitle: "Optional employer context", color: HDTheme.violet)
                            PremiumField(title: "Industry", icon: "square.grid.2x2", text: binding(\.industry))
                            PremiumField(title: "Headquarters", icon: "location.circle", text: binding(\.headquarters))
                            PremiumField(title: "Founded year", icon: "calendar", text: binding(\.foundedYear))
                            PremiumField(title: "Company website", icon: "globe", text: binding(\.companyWebsite))
                            PremiumField(title: "Careers URL", icon: "person.2.badge.gearshape", text: binding(\.careersUrl))
                            PremiumTextEditorField(
                                title: "Company overview",
                                icon: "building.2",
                                hint: "Short factual company context from an official source.",
                                text: binding(\.companyOverview),
                                minHeight: 100,
                                color: HDTheme.violet
                            )
                        }
                        .premiumCard()

                        PremiumTextEditorField(
                            title: "Eligibility",
                            icon: "checkmark.circle.fill",
                            hint: "Keep requirements readable. One idea per line or short paragraph.",
                            text: binding(\.elig),
                            minHeight: 110,
                            color: HDTheme.green
                        )

                        PremiumTextEditorField(
                            title: "Job description",
                            icon: "doc.text.fill",
                            hint: "Use short paragraphs with clear spacing. Avoid one dense text wall.",
                            text: binding(\.desc),
                            minHeight: 150,
                            color: HDTheme.blue
                        )

                        PremiumTextEditorField(
                            title: "Skills",
                            icon: "sparkles",
                            hint: "Comma-separated skills are shown as clean skill tags on the job page.",
                            text: listBinding(\.skills, commaSeparated: true),
                            minHeight: 90,
                            color: HDTheme.cyan
                        )

                        PremiumTextEditorField(
                            title: "Responsibilities",
                            icon: "checklist",
                            hint: "Use one responsibility per line so the public page becomes easy to scan.",
                            text: listBinding(\.resp),
                            minHeight: 130,
                            color: HDTheme.violet
                        )

                        PremiumTextEditorField(
                            title: "Who should apply",
                            icon: "person.crop.circle.badge.checkmark",
                            hint: "A concise candidate-fit paragraph works best.",
                            text: binding(\.who),
                            minHeight: 105,
                            color: HDTheme.green
                        )

                        PremiumTextEditorField(
                            title: "Selection process",
                            icon: "arrow.triangle.branch",
                            hint: "One stage per line: assessment, interview, HR, offer.",
                            text: listBinding(\.selectionProcess),
                            minHeight: 105,
                            color: HDTheme.amber
                        )

                        PremiumTextEditorField(
                            title: "Important dates",
                            icon: "calendar.badge.clock",
                            hint: "One date or deadline per line for a clean public timeline.",
                            text: listBinding(\.importantDates),
                            minHeight: 95,
                            color: HDTheme.red
                        )
                    }
                    .padding(16)
                    .padding(.bottom, 28)
                }
            }
            .navigationTitle("Edit Job")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                        .fontWeight(.black)
                }
            }
        }
    }
}

struct CheckerView: View {
    @EnvironmentObject private var state: AppState
    @State private var pendingRemove: AvailabilityItem?

    private var results: AvailabilityResponse.Results? {
        state.availability?.results
    }

    private var reviewItems: [AvailabilityItem] {
        results?.items?.filter { $0.state == "review" } ?? []
    }

    var body: some View {
        NavigationStack {
            ZStack {
                HDTheme.background.ignoresSafeArea()

                ScrollView {
                    VStack(spacing: 14) {
                        AdminHeader(
                            title: "Checker",
                            subtitle: "Official-link verification",
                            trailingSystemImage: "arrow.clockwise"
                        ) {
                            Task { await state.refreshChecker() }
                        }

                        ZStack {
                            LinearGradient(
                                colors: [
                                    reviewItems.isEmpty ? Color(red: 0.02, green: 0.46, blue: 0.35) : Color(red: 0.64, green: 0.37, blue: 0.03),
                                    reviewItems.isEmpty ? HDTheme.green : HDTheme.amber
                                ],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )

                            Circle()
                                .fill(Color.white.opacity(0.10))
                                .frame(width: 145, height: 145)
                                .offset(x: 145, y: -55)

                            HStack(spacing: 16) {
                                ZStack {
                                    Circle()
                                        .fill(Color.white.opacity(0.15))
                                        .frame(width: 78, height: 78)
                                    Image(systemName: reviewItems.isEmpty ? "checkmark.shield.fill" : "exclamationmark.triangle.fill")
                                        .font(.system(size: 32, weight: .bold))
                                        .foregroundStyle(.white)
                                }

                                VStack(alignment: .leading, spacing: 5) {
                                    Text(reviewItems.isEmpty ? "All clear" : "\\(reviewItems.count) need review")
                                        .font(.system(size: 24, weight: .black, design: .rounded))
                                        .foregroundStyle(.white)

                                    Text(reviewItems.isEmpty
                                         ? "No unresolved job availability checks."
                                         : "Open the official source before approving or expiring.")
                                        .font(.caption)
                                        .foregroundStyle(.white.opacity(0.82))
                                        .fixedSize(horizontal: false, vertical: true)
                                }

                                Spacer()
                            }
                            .padding(18)
                        }
                        .frame(height: 140)
                        .clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous))
                        .shadow(color: HDTheme.navy.opacity(0.10), radius: 14, x: 0, y: 7)

                        HStack(spacing: 8) {
                            PremiumMetricTile(title: "Active", value: numberText(results?.active), icon: "checkmark.circle.fill", color: HDTheme.green)
                            PremiumMetricTile(title: "Expired", value: numberText(results?.expired), icon: "xmark.circle.fill", color: HDTheme.red)
                            PremiumMetricTile(title: "Review", value: numberText(results?.review), icon: "exclamationmark.triangle.fill", color: HDTheme.amber)
                        }

                        VStack(alignment: .leading, spacing: 12) {
                            PremiumSectionTitle(
                                icon: "clock.arrow.circlepath",
                                title: "Checker controls",
                                subtitle: "Last run · \\(formatAdminDate(results?.checkedAt))",
                                color: HDTheme.blue
                            )

                            PremiumInfoBox(
                                icon: "hand.raised.fill",
                                title: "Conservative verification",
                                text: "Ambiguous links stay in review. Jobs are only expired when the official source clearly confirms closure or removal.",
                                color: HDTheme.blue
                            )

                            Button {
                                Task { await state.runChecker() }
                            } label: {
                                HStack(spacing: 8) {
                                    if state.isBusy { ProgressView().tint(.white) }
                                    Image(systemName: "play.fill")
                                    Text("Run checker now")
                                        .font(.subheadline.weight(.black))
                                }
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 14)
                            }
                            .buttonStyle(.plain)
                            .foregroundStyle(.white)
                            .background(
                                LinearGradient(
                                    colors: [HDTheme.navy, HDTheme.blue],
                                    startPoint: .leading,
                                    endPoint: .trailing
                                )
                            )
                            .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                            .disabled(state.isBusy)
                        }
                        .premiumCard()

                        if reviewItems.isEmpty {
                            PremiumInfoBox(
                                icon: "checkmark.circle.fill",
                                title: "No action required",
                                text: "The latest checker result has no unresolved review items.",
                                color: HDTheme.green
                            )
                            .premiumCard(10)
                        } else {
                            VStack(alignment: .leading, spacing: 10) {
                                PremiumSectionTitle(
                                    icon: "tray.full.fill",
                                    title: "Review queue",
                                    subtitle: "Verify against the official employer page",
                                    color: HDTheme.amber
                                )

                                ForEach(reviewItems) { item in
                                    ReviewItemCard(
                                        item: item,
                                        remove: { pendingRemove = item },
                                        keep: {
                                            Task { await state.resolveReview(item, action: "keep") }
                                        }
                                    )
                                }
                            }
                        }
                    }
                    .padding(16)
                    .padding(.bottom, 18)
                }
                .refreshable { await state.refreshChecker() }
            }
            .toolbar(.hidden, for: .navigationBar)
            .confirmationDialog(
                pendingRemove?.pendingNew == true ? "Reject this unpublished job?" : "Mark this job expired?",
                isPresented: Binding(
                    get: { pendingRemove != nil },
                    set: { if !$0 { pendingRemove = nil } }
                ),
                titleVisibility: .visible
            ) {
                Button(pendingRemove?.pendingNew == true ? "Reject / Do Not Publish" : "Remove / Mark Expired", role: .destructive) {
                    if let item = pendingRemove {
                        Task { await state.resolveReview(item, action: "expire") }
                    }
                    pendingRemove = nil
                }
                Button("Cancel", role: .cancel) { pendingRemove = nil }
            }
        }
    }
}

struct ReviewItemCard: View {
    let item: AvailabilityItem
    let remove: () -> Void
    let keep: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 11) {
            HStack(alignment: .top, spacing: 10) {
                Image(systemName: "questionmark.diamond.fill")
                    .font(.system(size: 15, weight: .bold))
                    .foregroundStyle(HDTheme.amber)
                    .frame(width: 38, height: 38)
                    .background(HDTheme.amber.opacity(0.10))
                    .clipShape(RoundedRectangle(cornerRadius: 11, style: .continuous))

                VStack(alignment: .leading, spacing: 3) {
                    Text(item.company ?? "Company")
                        .font(.subheadline.weight(.black))
                        .foregroundStyle(HDTheme.navy)
                    Text(item.role ?? "Job Opening")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                }

                Spacer()

                StatusPill(
                    text: item.pendingNew == true ? "Review to publish" : "Needs review",
                    color: HDTheme.amber
                )
            }

            PremiumInfoBox(
                icon: "info.circle.fill",
                title: "Why this needs review",
                text: item.reason ?? "Availability could not be confirmed.",
                color: HDTheme.amber
            )

            HStack(spacing: 8) {
                if let official = item.url.flatMap(URL.init(string:)) {
                    Link(destination: official) {
                        Label("Official", systemImage: "arrow.up.right.square")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.bordered)
                }

                if item.pendingNew != true, let hd = siteURL(item.page) {
                    Link(destination: hd) {
                        Label("HD Careers", systemImage: "eye")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.bordered)
                }
            }

            HStack(spacing: 8) {
                Button(role: .destructive, action: remove) {
                    Label(item.pendingNew == true ? "Reject" : "Expire", systemImage: "xmark")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)

                Button(action: keep) {
                    Label(item.pendingNew == true ? "Approve & publish" : "Keep active", systemImage: "checkmark")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .tint(HDTheme.green)
            }
        }
        .premiumCard(13)
    }
}

struct MoreView: View {
    @EnvironmentObject private var state: AppState

    var body: some View {
        NavigationStack {
            ZStack {
                HDTheme.background.ignoresSafeArea()

                ScrollView {
                    VStack(spacing: 14) {
                        AdminHeader(title: "More", subtitle: "Tools and account")

                        ZStack {
                            LinearGradient(
                                colors: [HDTheme.navy, HDTheme.violet],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )

                            Circle()
                                .fill(Color.white.opacity(0.08))
                                .frame(width: 130, height: 130)
                                .offset(x: 145, y: -50)

                            HStack(spacing: 14) {
                                ZStack {
                                    Circle()
                                        .fill(Color.white.opacity(0.14))
                                        .frame(width: 62, height: 62)
                                    Text("C")
                                        .font(.title2.weight(.black))
                                        .foregroundStyle(.white)
                                }

                                VStack(alignment: .leading, spacing: 3) {
                                    Text("Chethan")
                                        .font(.title3.weight(.black))
                                        .foregroundStyle(.white)
                                    Text("Private administrator")
                                        .font(.caption)
                                        .foregroundStyle(.white.opacity(0.72))
                                    HStack(spacing: 5) {
                                        Circle().fill(HDTheme.green).frame(width: 6, height: 6)
                                        Text("Admin session active")
                                            .font(.caption2.weight(.semibold))
                                            .foregroundStyle(.white.opacity(0.82))
                                    }
                                }

                                Spacer()
                            }
                            .padding(18)
                        }
                        .frame(height: 116)
                        .clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous))
                        .shadow(color: HDTheme.navy.opacity(0.12), radius: 14, x: 0, y: 7)

                        VStack(spacing: 0) {
                            NavigationLink {
                                AnalyticsView()
                            } label: {
                                MoreRow(icon: "chart.bar.fill", title: "Website analytics", subtitle: "Traffic, conversions and content", color: HDTheme.blue)
                            }
                            Divider().padding(.leading, 58)

                            NavigationLink {
                                AutomationDetailsView()
                            } label: {
                                MoreRow(icon: "bolt.horizontal.circle.fill", title: "Publishing automation", subtitle: "Daily batch and workflow status", color: HDTheme.green)
                            }
                            Divider().padding(.leading, 58)

                            if let adminURL = URL(string: "https://hdcareers.in/admin/") {
                                Link(destination: adminURL) {
                                    MoreRow(icon: "safari.fill", title: "Web admin", subtitle: "Open the browser control center", color: HDTheme.violet)
                                }
                            }
                            Divider().padding(.leading, 58)

                            if let site = URL(string: "https://hdcareers.in") {
                                Link(destination: site) {
                                    MoreRow(icon: "globe", title: "HD Careers website", subtitle: "View the public site", color: HDTheme.cyan)
                                }
                            }
                        }
                        .premiumCard(0)

                        VStack(spacing: 0) {
                            if CredentialVault.load() != nil {
                                Button(role: .destructive) {
                                    state.removeSavedFaceID()
                                } label: {
                                    MoreRow(icon: "faceid", title: "Face ID", subtitle: "Remove saved biometric login", color: HDTheme.amber)
                                }
                                .buttonStyle(.plain)
                                Divider().padding(.leading, 58)
                            }

                            Button(role: .destructive) {
                                Task { await state.logout() }
                            } label: {
                                MoreRow(icon: "rectangle.portrait.and.arrow.right", title: "Sign out", subtitle: "End this admin session", color: HDTheme.red)
                            }
                            .buttonStyle(.plain)
                        }
                        .premiumCard(0)
                    }
                    .padding(16)
                    .padding(.bottom, 18)
                }
            }
            .toolbar(.hidden, for: .navigationBar)
        }
    }
}

struct MoreRow: View {
    let icon: String
    let title: String
    let subtitle: String?
    let color: Color

    init(icon: String, title: String, subtitle: String? = nil, color: Color) {
        self.icon = icon
        self.title = title
        self.subtitle = subtitle
        self.color = color
    }

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .font(.system(size: 14, weight: .bold))
                .foregroundStyle(color)
                .frame(width: 38, height: 38)
                .background(color.opacity(0.09))
                .clipShape(RoundedRectangle(cornerRadius: 11, style: .continuous))

            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.subheadline.weight(.bold))
                    .foregroundStyle(HDTheme.navy)
                if let subtitle {
                    Text(subtitle)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }
            }

            Spacer()

            Image(systemName: "chevron.right")
                .font(.caption.weight(.bold))
                .foregroundStyle(.tertiary)
        }
        .padding(14)
        .contentShape(Rectangle())
    }
}

struct AnalyticsView: View {
    @EnvironmentObject private var state: AppState

    private var topPageName: String {
        guard let top = state.traffic?.pages?.first else { return "No data yet" }
        return jobDisplayName(path: top.requestPath, jobs: state.jobs)
    }

    var body: some View {
        ZStack {
            HDTheme.background.ignoresSafeArea()

            ScrollView {
                VStack(spacing: 13) {
                    ZStack {
                        LinearGradient(
                            colors: [HDTheme.navy, HDTheme.blue, HDTheme.violet],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )

                        Circle()
                            .fill(Color.white.opacity(0.08))
                            .frame(width: 150, height: 150)
                            .offset(x: 145, y: -55)

                        VStack(alignment: .leading, spacing: 13) {
                            HStack {
                                VStack(alignment: .leading, spacing: 3) {
                                    Text("ANALYTICS")
                                        .font(.system(size: 10, weight: .black))
                                        .tracking(1.1)
                                        .foregroundStyle(.white.opacity(0.70))
                                    Text("Performance at a glance")
                                        .font(.system(size: 23, weight: .black, design: .rounded))
                                        .foregroundStyle(.white)
                                }
                                Spacer()
                                Image(systemName: "chart.bar.xaxis")
                                    .font(.system(size: 24, weight: .bold))
                                    .foregroundStyle(.white.opacity(0.9))
                            }

                            HStack(spacing: 8) {
                                analyticsHeroMetric("Live", numberText(state.traffic?.realtimeUsers))
                                analyticsHeroMetric("Users", numberText(state.traffic?.totals?.visitors))
                                analyticsHeroMetric("Views", numberText(state.traffic?.totals?.pageviews))
                            }
                        }
                        .padding(18)
                    }
                    .frame(height: 170)
                    .clipShape(RoundedRectangle(cornerRadius: 23, style: .continuous))
                    .shadow(color: HDTheme.navy.opacity(0.13), radius: 15, x: 0, y: 8)

                    Picker("Period", selection: Binding(
                        get: { state.trafficDays },
                        set: { days in Task { await state.loadTraffic(days: days) } }
                    )) {
                        Text("24H").tag(1)
                        Text("7D").tag(7)
                        Text("30D").tag(30)
                    }
                    .pickerStyle(.segmented)

                    ConversionSummaryCard()

                    PremiumInfoBox(
                        icon: "flame.fill",
                        title: "Top content",
                        text: topPageName,
                        color: HDTheme.amber
                    )
                    .premiumCard(10)

                    AnalyticsListCard(
                        title: "Top apply jobs",
                        icon: "arrow.up.right.square.fill",
                        rows: (state.traffic?.applyJobs ?? []).map {
                            (jobDisplayName(path: $0.requestPath, jobs: state.jobs), $0.count ?? 0)
                        }
                    )

                    AnalyticsListCard(
                        title: "Resume checker usage",
                        icon: "doc.text.magnifyingglass",
                        rows: (state.traffic?.resumeJobs ?? []).map {
                            (jobDisplayName(path: $0.requestPath, jobs: state.jobs), $0.count ?? 0)
                        }
                    )

                    AnalyticsListCard(
                        title: "Traffic sources",
                        icon: "point.3.connected.trianglepath.dotted",
                        rows: (state.traffic?.referrers ?? []).map {
                            (($0.referrerHostname?.isEmpty == false ? $0.referrerHostname! : "Direct / Unknown"), $0.sessions ?? 0)
                        }
                    )

                    HStack(alignment: .top, spacing: 10) {
                        AnalyticsListCard(
                            title: "Countries",
                            icon: "globe.asia.australia.fill",
                            rows: (state.traffic?.countries ?? []).map {
                                ($0.country ?? "Unknown", $0.visitors ?? 0)
                            }
                        )

                        AnalyticsListCard(
                            title: "Devices",
                            icon: "iphone",
                            rows: (state.traffic?.devices ?? []).map {
                                (($0.deviceType ?? "Unknown").capitalized, $0.visitors ?? 0)
                            }
                        )
                    }
                }
                .padding(16)
                .padding(.bottom, 18)
            }
        }
        .navigationTitle("Analytics")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func analyticsHeroMetric(_ title: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 1) {
            Text(value)
                .font(.headline.weight(.black))
                .foregroundStyle(.white)
            Text(title)
                .font(.system(size: 8.5, weight: .semibold))
                .foregroundStyle(.white.opacity(0.65))
        }
        .padding(.horizontal, 11)
        .padding(.vertical, 8)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.white.opacity(0.10))
        .clipShape(RoundedRectangle(cornerRadius: 11, style: .continuous))
    }
}

struct ConversionSummaryCard: View {
    @EnvironmentObject private var state: AppState

    private var conversions: TrafficResponse.Conversions? { state.traffic?.conversions }
    private var maxValue: Int {
        max(
            conversions?.jobPageViews ?? 0,
            conversions?.resumeChecks ?? 0,
            conversions?.applyClicks ?? 0,
            conversions?.applyUsers ?? 0,
            1
        )
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 13) {
            HStack {
                PremiumSectionTitle(
                    icon: "point.3.connected.trianglepath.dotted",
                    title: "Conversion funnel",
                    subtitle: "Job view → resume → official apply",
                    color: HDTheme.violet
                )
                Text(String(format: "%.1f%%", conversions?.applyRate ?? 0))
                    .font(.title3.weight(.black))
                    .foregroundStyle(HDTheme.violet)
            }

            HStack(spacing: 8) {
                PremiumMetricTile(title: "Job views", value: numberText(conversions?.jobPageViews), icon: "eye.fill", color: HDTheme.blue)
                PremiumMetricTile(title: "Resume", value: numberText(conversions?.resumeChecks), icon: "doc.text.magnifyingglass", color: HDTheme.cyan)
                PremiumMetricTile(title: "Apply", value: numberText(conversions?.applyClicks), icon: "cursorarrow.click.2", color: HDTheme.green)
            }

            VStack(spacing: 8) {
                PremiumBarRow(title: "Job views", value: conversions?.jobPageViews ?? 0, maxValue: maxValue, color: HDTheme.blue)
                PremiumBarRow(title: "Resume checks", value: conversions?.resumeChecks ?? 0, maxValue: maxValue, color: HDTheme.cyan)
                PremiumBarRow(title: "Apply clicks", value: conversions?.applyClicks ?? 0, maxValue: maxValue, color: HDTheme.green)
                PremiumBarRow(title: "Apply users", value: conversions?.applyUsers ?? 0, maxValue: maxValue, color: HDTheme.violet)
            }
        }
        .premiumCard()
    }
}

struct AnalyticsListCard: View {
    let title: String
    let icon: String
    let rows: [(String, Int)]

    private var visibleRows: [(String, Int)] {
        Array(rows.prefix(6))
    }

    private var maxValue: Int {
        max(visibleRows.map(\.1).max() ?? 1, 1)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            PremiumSectionTitle(icon: icon, title: title, subtitle: visibleRows.isEmpty ? "No data yet" : "Top \\(visibleRows.count)")

            if visibleRows.isEmpty {
                Text("No data for this period.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, alignment: .leading)
            } else {
                ForEach(Array(visibleRows.enumerated()), id: \.offset) { index, row in
                    VStack(spacing: 6) {
                        HStack(spacing: 8) {
                            Text("\\(index + 1)")
                                .font(.system(size: 9, weight: .black))
                                .foregroundStyle(HDTheme.blue)
                                .frame(width: 24, height: 24)
                                .background(HDTheme.blue.opacity(0.08))
                                .clipShape(Circle())

                            Text(row.0)
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(HDTheme.navy)
                                .lineLimit(2)

                            Spacer()

                            Text(numberText(row.1))
                                .font(.caption.weight(.black))
                                .foregroundStyle(HDTheme.navy)
                        }

                        GeometryReader { geo in
                            ZStack(alignment: .leading) {
                                Capsule().fill(Color.black.opacity(0.05))
                                Capsule()
                                    .fill(
                                        LinearGradient(
                                            colors: [HDTheme.blue, HDTheme.cyan],
                                            startPoint: .leading,
                                            endPoint: .trailing
                                        )
                                    )
                                    .frame(width: geo.size.width * CGFloat(row.1) / CGFloat(maxValue))
                            }
                        }
                        .frame(height: 4)
                    }

                    if index != visibleRows.count - 1 {
                        Divider().opacity(0.45)
                    }
                }
            }
        }
        .premiumCard()
    }
}

struct AutomationDetailsView: View {
    @EnvironmentObject private var state: AppState

    private func statusColor(_ outcome: String?) -> Color {
        switch outcome {
        case "published": return HDTheme.green
        case "partial", "no_publish": return HDTheme.amber
        case "error": return HDTheme.red
        case "scheduled": return HDTheme.blue
        default: return HDTheme.blue
        }
    }

    private func statusLabel(_ outcome: String?) -> String {
        if outcome == "scheduled" { return "Ready" }
        return outcome?.replacingOccurrences(of: "_", with: " ").capitalized ?? "Scheduled"
    }

    var body: some View {
        ZStack {
            HDTheme.background.ignoresSafeArea()

            ScrollView {
                VStack(spacing: 12) {
                    if let slot = state.automationHealth?.slots.first(where: { $0.enabled }) {
                        VStack(alignment: .leading, spacing: 14) {
                            HStack {
                                Circle()
                                    .fill(statusColor(slot.outcome))
                                    .frame(width: 10, height: 10)
                                VStack(alignment: .leading, spacing: 2) {
                                    Text("\(slot.time) — \(slot.title)")
                                        .font(.headline.weight(.black))
                                    if let target = slot.target {
                                        Text(target)
                                            .font(.caption.weight(.bold))
                                            .foregroundStyle(HDTheme.blue)
                                    }
                                }
                                Spacer()
                                StatusPill(text: statusLabel(slot.outcome), color: statusColor(slot.outcome))
                            }

                            if let mix = slot.mix, !mix.isEmpty {
                                LazyVGrid(columns: [GridItem(.adaptive(minimum: 118), spacing: 8)], alignment: .leading, spacing: 8) {
                                    ForEach(mix, id: \.self) { item in
                                        Text(item)
                                            .font(.caption2.weight(.bold))
                                            .foregroundStyle(HDTheme.navy)
                                            .padding(.horizontal, 9)
                                            .padding(.vertical, 7)
                                            .background(HDTheme.blue.opacity(0.07))
                                            .clipShape(Capsule())
                                    }
                                }
                            }

                            if let delivery = slot.delivery, !delivery.isEmpty {
                                Label(delivery, systemImage: "arrow.triangle.branch")
                                    .font(.subheadline.weight(.semibold))
                                    .foregroundStyle(HDTheme.green)
                            }

                            if let next = slot.nextRunAt {
                                Label("Next run: \(formatAdminDate(next))", systemImage: "calendar.badge.clock")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }

                            if let last = slot.lastRunAt {
                                Text("Previous run: \(formatAdminDate(last))")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }

                            if let detail = slot.detail, !detail.isEmpty {
                                Text(detail)
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                            }
                        }
                        .hdCard()
                    } else {
                        EmptyState(icon: "bolt.slash", title: "No active publishing automation", message: "Refresh the dashboard to load the current daily batch.")
                            .hdCard()
                    }
                }
                .padding(16)
            }
        }
        .navigationTitle("Daily Publishing Batch")
        .navigationBarTitleDisplayMode(.inline)
    }
}
