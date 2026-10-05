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
                        TrafficTrendCard()
                        AudienceAnalyticsCard()
                        AcquisitionAnalyticsCard()
                        ConversionAnalyticsCard()
                        TopContentAnalyticsCard()
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

    var body: some View {
        ZStack(alignment: .bottomLeading) {
            LinearGradient(
                colors: [HDTheme.navy, HDTheme.blue],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .frame(height: 178)
            .clipShape(RoundedRectangle(cornerRadius: 24, style: .continuous))

            Circle()
                .fill(Color.white.opacity(0.10))
                .frame(width: 150, height: 150)
                .offset(x: 245, y: -55)

            VStack(alignment: .leading, spacing: 9) {
                HStack {
                    Image(systemName: "sparkles")
                    Text("HD CAREERS CONTROL CENTER")
                        .font(.caption2.weight(.black))
                        .tracking(1.1)
                }
                .foregroundStyle(.white.opacity(0.78))

                Text("Everything important,\nright here.")
                    .font(.system(size: 28, weight: .black, design: .rounded))
                    .foregroundStyle(.white)

                HStack(spacing: 8) {
                    Label("\(state.activeJobs.count) live jobs", systemImage: "briefcase.fill")
                    if reviewCount > 0 {
                        Label("\(reviewCount) to review", systemImage: "exclamationmark.triangle.fill")
                    } else {
                        Label("All clear", systemImage: "checkmark.shield.fill")
                    }
                }
                .font(.caption.weight(.bold))
                .foregroundStyle(.white.opacity(0.9))
            }
            .padding(20)
        }
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
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Jobs overview")
                        .font(.headline.weight(.black))
                    Text("Current website inventory")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                StatusPill(text: "\(state.activeJobs.count) active", color: HDTheme.green, icon: "checkmark.circle.fill")
            }

            LazyVGrid(columns: columns, spacing: 8) {
                DashboardStat(title: "Total", value: state.jobs.count, icon: "briefcase.fill", color: HDTheme.blue)
                DashboardStat(title: "Freshers", value: state.fresherJobs.count, icon: "person.crop.circle.badge.checkmark", color: .purple)
                DashboardStat(title: "Active", value: state.activeJobs.count, icon: "checkmark.circle.fill", color: HDTheme.green)
                DashboardStat(title: "Expired", value: state.expiredJobs.count, icon: "xmark.circle.fill", color: HDTheme.red)
            }
        }
        .hdCard()
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
        case 1: return "Last 24 hours"
        case 30: return "Last 30 days"
        default: return "Last 7 days"
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Website traffic")
                        .font(.headline.weight(.black))
                    Text("Live GA4 snapshot · \(periodLabel)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                StatusPill(text: "Live", color: HDTheme.green, icon: "circle.fill")
            }

            Picker("Period", selection: Binding(
                get: { state.trafficDays },
                set: { days in Task { await state.loadTraffic(days: days) } }
            )) {
                Text("24H").tag(1)
                Text("7D").tag(7)
                Text("30D").tag(30)
            }
            .pickerStyle(.segmented)

            HStack(spacing: 0) {
                TrafficMetric(
                    title: "Live",
                    value: state.traffic?.realtimeUsers ?? 0,
                    icon: "dot.radiowaves.left.and.right",
                    color: HDTheme.green
                )
                Divider().frame(height: 44)
                TrafficMetric(
                    title: "Users",
                    value: state.traffic?.totals?.visitors ?? 0,
                    icon: "person.2.fill",
                    color: HDTheme.blue
                )
                Divider().frame(height: 44)
                TrafficMetric(
                    title: "Views",
                    value: state.traffic?.totals?.pageviews ?? 0,
                    icon: "eye.fill",
                    color: .purple
                )
            }

            HStack(spacing: 8) {
                AnalyticsMiniMetric(
                    title: "Sessions",
                    value: numberText(state.traffic?.totals?.sessions),
                    icon: "rectangle.stack.fill"
                )
                AnalyticsMiniMetric(
                    title: "Views / user",
                    value: String(format: "%.2f", state.traffic?.totals?.viewsPerUser ?? 0),
                    icon: "chart.line.uptrend.xyaxis"
                )
                AnalyticsMiniMetric(
                    title: "Engagement",
                    value: String(format: "%.1f%%", state.traffic?.totals?.engagementRate ?? 0),
                    icon: "bolt.heart.fill"
                )
            }
        }
        .hdCard()
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
                    VStack(spacing: 14) {
                        AdminHeader(
                            title: "All Jobs",
                            subtitle: "\(state.jobs.count) published jobs",
                            trailingSystemImage: "arrow.clockwise"
                        ) {
                            Task { await state.refreshJobs() }
                        }

                        HStack {
                            Image(systemName: "magnifyingglass")
                                .foregroundStyle(.secondary)
                            TextField("Search title, company or location", text: $search)
                                .textInputAutocapitalization(.never)
                        }
                        .padding(12)
                        .background(.white)
                        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))

                        Picker("Status", selection: $filter) {
                            ForEach(JobListFilter.allCases) { item in
                                Text("\(item.rawValue) \(count(for: item))").tag(item)
                            }
                        }
                        .pickerStyle(.segmented)

                        if filteredJobs.isEmpty {
                            EmptyState(icon: "briefcase", title: "No jobs found", message: "Try changing your search or status filter.")
                                .hdCard()
                        } else {
                            LazyVStack(spacing: 10) {
                                ForEach(filteredJobs) { job in
                                    JobRow(job: job)
                                }
                            }
                        }
                    }
                    .padding(16)
                    .padding(.bottom, 16)
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
            CompanyLogoView(job: job, size: 46)

            VStack(alignment: .leading, spacing: 5) {
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(job.company ?? "Company")
                            .font(.headline.weight(.black))
                        Text(job.role ?? "Job Opening")
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(.secondary)
                            .lineLimit(2)
                    }
                    Spacer(minLength: 8)
                    StatusPill(
                        text: job.isExpired ? "Expired" : "Active",
                        color: job.isExpired ? HDTheme.red : HDTheme.green
                    )
                }

                HStack(spacing: 8) {
                    Label(job.loc ?? "Not specified", systemImage: "mappin.and.ellipse")
                    Label(job.expType?.capitalized ?? "Job", systemImage: "person.fill")
                }
                .font(.caption2)
                .foregroundStyle(.secondary)
                .lineLimit(1)

                HStack(spacing: 12) {
                    if let site = job.siteURL {
                        Link("HD Careers", destination: site)
                    }
                    if let official = job.officialURL {
                        Link("Official ↗", destination: official)
                    }
                }
                .font(.caption.weight(.bold))
                .foregroundStyle(HDTheme.blue)
            }
        }
        .hdCard(14)
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
                    VStack(spacing: 16) {
                        AdminHeader(title: "Add / Publish Jobs", subtitle: "Private publishing workflow")

                        VStack(alignment: .leading, spacing: 13) {
                            HStack {
                                Label("Paste Official Job Links", systemImage: "link")
                                    .font(.headline.weight(.black))
                                Spacer()
                                StatusPill(
                                    text: "\(readyLinks.count) ready",
                                    color: readyLinks.isEmpty ? Color.gray : HDTheme.green,
                                    icon: readyLinks.isEmpty ? "link" : "checkmark.circle.fill"
                                )
                            }

                            Text("Paste up to 20 official employer URLs, one per line.")
                                .font(.caption)
                                .foregroundStyle(.secondary)

                            TextEditor(text: $rawLinks)
                                .frame(minHeight: 120)
                                .padding(9)
                                .scrollContentBackground(.hidden)
                                .background(Color(.secondarySystemBackground))
                                .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))

                            if parsedLinks.isEmpty {
                                EmptyState(icon: "link", title: "No links yet", message: "Paste official job URLs above to preview them.")
                                    .padding(.vertical, -6)
                            } else {
                                VStack(spacing: 8) {
                                    ForEach(parsedLinks) { item in
                                        LinkPreviewRow(item: item) {
                                            removeLink(at: item.lineIndex)
                                        }
                                    }
                                }
                            }

                            Button {
                                Task { await generateJobs() }
                            } label: {
                                HStack {
                                    if isGenerating {
                                        ProgressView().tint(.white)
                                    } else {
                                        Image(systemName: "wand.and.stars")
                                    }
                                    Text(isGenerating ? "Generating \(processed)/\(readyLinks.count)…" : "Generate \(readyLinks.count) job\(readyLinks.count == 1 ? "" : "s")")
                                        .fontWeight(.bold)
                                }
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 14)
                            }
                            .buttonStyle(.plain)
                            .foregroundStyle(.white)
                            .background(readyLinks.isEmpty || isGenerating ? Color.gray.opacity(0.5) : HDTheme.blue)
                            .clipShape(RoundedRectangle(cornerRadius: 15, style: .continuous))
                            .disabled(readyLinks.isEmpty || isGenerating)
                        }
                        .hdCard()

                        if !extractionIssues.isEmpty {
                            VStack(alignment: .leading, spacing: 8) {
                                Label("Extraction issues", systemImage: "exclamationmark.triangle.fill")
                                    .font(.headline)
                                    .foregroundStyle(HDTheme.amber)
                                ForEach(extractionIssues, id: \.self) { issue in
                                    Text("• \(issue)")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                            }
                            .hdCard()
                        }

                        if !drafts.isEmpty {
                            VStack(alignment: .leading, spacing: 12) {
                                HStack {
                                    Text("Generated Preview")
                                        .font(.headline.weight(.black))
                                    Spacer()
                                    Text("\(selectedDrafts.count) selected")
                                        .font(.caption.weight(.bold))
                                        .foregroundStyle(.secondary)
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

                                Button {
                                    showPublishConfirmation = true
                                } label: {
                                    Label(
                                        "Publish \(selectedDrafts.count) to HD Careers",
                                        systemImage: "arrow.up.circle.fill"
                                    )
                                    .fontWeight(.bold)
                                    .frame(maxWidth: .infinity)
                                    .padding(.vertical, 14)
                                }
                                .buttonStyle(.plain)
                                .foregroundStyle(.white)
                                .background(selectedDrafts.isEmpty ? Color.gray.opacity(0.5) : HDTheme.blue)
                                .clipShape(RoundedRectangle(cornerRadius: 15, style: .continuous))
                                .disabled(selectedDrafts.isEmpty || state.isBusy)
                            }
                            .hdCard()
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
                Button("Publish \(selectedDrafts.count) jobs") {
                    Task { await publishSelected() }
                }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("The existing HD Careers validation, generation, Vercel deployment and Telegram workflow will run.")
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
                            return (index, nil, "\(link.domain): \(error.localizedDescription)")
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
        return "Ready"
    }

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: item.valid ? "link" : "exclamationmark.triangle.fill")
                .foregroundStyle(color)
                .frame(width: 34, height: 34)
                .background(color.opacity(0.10))
                .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))

            VStack(alignment: .leading, spacing: 3) {
                HStack {
                    Text(item.domain)
                        .font(.subheadline.weight(.black))
                        .lineLimit(1)
                    StatusPill(text: status, color: color)
                }
                Text(item.path)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }

            Spacer(minLength: 4)

            HStack(spacing: 8) {
                if let url = item.url, item.valid {
                    Link(destination: url) {
                        Image(systemName: "arrow.up.right")
                    }
                }
                Button(action: remove) {
                    Image(systemName: "xmark")
                }
                .buttonStyle(.plain)
                .foregroundStyle(.secondary)
            }
            .font(.caption.weight(.bold))
        }
        .padding(10)
        .background(color.opacity(0.035))
        .clipShape(RoundedRectangle(cornerRadius: 13, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 13, style: .continuous)
                .stroke(color.opacity(0.18))
        }
    }
}

struct DraftJobRow: View {
    let job: Job
    let selected: Bool
    let toggle: () -> Void
    let edit: () -> Void

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Button(action: toggle) {
                Image(systemName: selected ? "checkmark.circle.fill" : "circle")
                    .foregroundStyle(selected ? HDTheme.blue : .secondary)
                    .font(.title3)
            }
            .buttonStyle(.plain)

            CompanyLogoView(job: job, size: 42)

            VStack(alignment: .leading, spacing: 4) {
                Text(job.company ?? "Company")
                    .font(.headline.weight(.black))
                Text(job.role ?? "Job Opening")
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(.secondary)
                HStack {
                    StatusPill(text: job.cat?.capitalized ?? "Job", color: HDTheme.blue)
                    Text(job.loc ?? "Location not specified")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }
            }

            Spacer()

            Button(action: edit) {
                Image(systemName: "pencil")
                    .font(.caption.weight(.bold))
                    .padding(9)
                    .background(HDTheme.blue.opacity(0.08))
                    .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
            }
            .buttonStyle(.plain)
        }
        .padding(12)
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
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
            Form {
                Section("Basics") {
                    TextField("Company", text: binding(\.company))
                    TextField("Role", text: binding(\.role))
                    TextField("Location", text: binding(\.loc))
                    TextField("Experience", text: binding(\.expYears))
                    TextField("Batch / Qualification", text: binding(\.batch))
                    TextField("Salary", text: binding(\.salary))
                    TextField("Work mode", text: binding(\.workMode))
                }

                Section("Official source") {
                    TextField("Official apply URL", text: binding(\.apply))
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    TextField("Source name", text: binding(\.sourceName))
                    TextField("Verified date", text: binding(\.verifiedDate))
                    TextField("Closing date", text: binding(\.closingAt))
                    TextField("Job / Requisition ID", text: binding(\.externalJobId))
                    TextField("Careers favicon URL", text: binding(\.careerIconUrl))
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    TextField("Full logo URL (fallback)", text: binding(\.logoUrl))
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                }

                Section {
                    TextField("Industry", text: binding(\.industry))
                    TextField("Headquarters", text: binding(\.headquarters))
                    TextField("Founded year", text: binding(\.foundedYear))
                    TextField("Company website", text: binding(\.companyWebsite))
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    TextField("Careers URL", text: binding(\.careersUrl))
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    TextEditor(text: binding(\.companyOverview))
                        .frame(minHeight: 100)
                } header: {
                    Text("Optional company details")
                } footer: {
                    Text("Use only information supported by the official source. Blank fields are allowed.")
                }

                Section("Eligibility") {
                    TextEditor(text: binding(\.elig))
                        .frame(minHeight: 100)
                }

                Section("Description") {
                    TextEditor(text: binding(\.desc))
                        .frame(minHeight: 130)
                }

                Section("Skills") {
                    TextEditor(text: listBinding(\.skills, commaSeparated: true))
                        .frame(minHeight: 90)
                }

                Section("Responsibilities") {
                    TextEditor(text: listBinding(\.resp))
                        .frame(minHeight: 120)
                }

                Section("Who should apply") {
                    TextEditor(text: binding(\.who))
                        .frame(minHeight: 90)
                }

                Section("Selection process") {
                    TextEditor(text: listBinding(\.selectionProcess))
                        .frame(minHeight: 100)
                }

                Section("Important dates") {
                    TextEditor(text: listBinding(\.importantDates))
                        .frame(minHeight: 90)
                }
            }
            .navigationTitle("Edit Job")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                        .fontWeight(.bold)
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
                    VStack(spacing: 16) {
                        AdminHeader(
                            title: "Expired Job Checker",
                            subtitle: "Conservative official-link verification",
                            trailingSystemImage: "arrow.clockwise"
                        ) {
                            Task { await state.refreshChecker() }
                        }

                        VStack(alignment: .leading, spacing: 14) {
                            HStack {
                                VStack(alignment: .leading, spacing: 3) {
                                    Text("Last Run")
                                        .font(.caption.weight(.bold))
                                        .foregroundStyle(.secondary)
                                    Text(formatAdminDate(results?.checkedAt))
                                        .font(.subheadline.weight(.black))
                                }
                                Spacer()
                                StatusPill(
                                    text: state.availability?.latestRun?.status?.capitalized ?? "Saved",
                                    color: HDTheme.green,
                                    icon: "checkmark.circle.fill"
                                )
                            }

                            HStack(spacing: 10) {
                                SmallMetric(title: "Expired", value: results?.expired ?? 0, color: HDTheme.red)
                                SmallMetric(title: "Needs Review", value: results?.review ?? 0, color: HDTheme.amber)
                                SmallMetric(title: "No Change", value: results?.active ?? 0, color: HDTheme.green)
                            }

                            Button {
                                Task { await state.runChecker() }
                            } label: {
                                HStack {
                                    if state.isBusy { ProgressView().tint(.white) }
                                    Image(systemName: "play.fill")
                                    Text("Run Checker Now").fontWeight(.bold)
                                }
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 14)
                            }
                            .buttonStyle(.plain)
                            .foregroundStyle(.white)
                            .background(HDTheme.amber)
                            .clipShape(RoundedRectangle(cornerRadius: 15, style: .continuous))
                            .disabled(state.isBusy)
                        }
                        .hdCard()

                        if reviewItems.isEmpty {
                            VStack(spacing: 8) {
                                Image(systemName: "checkmark.shield.fill")
                                    .font(.system(size: 30))
                                    .foregroundStyle(HDTheme.green)
                                Text("No jobs need review")
                                    .font(.headline.weight(.black))
                                Text("The current checker result has no unresolved review items.")
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                                    .multilineTextAlignment(.center)
                            }
                            .frame(maxWidth: .infinity)
                            .hdCard()
                        } else {
                            VStack(alignment: .leading, spacing: 12) {
                                Text("Needs Review (\(reviewItems.count))")
                                    .font(.headline.weight(.black))

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
                    .padding(.bottom, 16)
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
            } message: {
                Text(pendingRemove?.pendingNew == true
                     ? "This job is still unpublished. Rejecting it removes it from Needs Review and it will not be published."
                     : "This will mark the job expired in HD Careers and trigger the normal website regeneration.")
            }
        }
    }
}

struct ReviewItemCard: View {
    let item: AvailabilityItem
    let remove: () -> Void
    let keep: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 3) {
                    Text(item.company ?? "Company")
                        .font(.headline.weight(.black))
                    Text(item.role ?? "Job Opening")
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(.secondary)
                }
                Spacer()
                StatusPill(text: item.pendingNew == true ? "Review to Publish" : "Needs Review", color: HDTheme.amber)
            }

            Text(item.reason ?? "Availability could not be confirmed.")
                .font(.caption)
                .foregroundStyle(.secondary)

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
                    Label(item.pendingNew == true ? "Reject" : "Remove", systemImage: "trash.fill")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)

                Button(action: keep) {
                    Label(item.pendingNew == true ? "Approve & Publish" : "Keep Active", systemImage: item.pendingNew == true ? "paperplane.fill" : "checkmark")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .tint(HDTheme.green)
            }
        }
        .hdCard(14)
    }
}

struct MoreView: View {
    @EnvironmentObject private var state: AppState

    var body: some View {
        NavigationStack {
            ZStack {
                HDTheme.background.ignoresSafeArea()
                ScrollView {
                    VStack(spacing: 16) {
                        AdminHeader(title: "More", subtitle: "HD Careers Admin")

                        HStack(spacing: 14) {
                            Circle()
                                .fill(HDTheme.blue.opacity(0.12))
                                .frame(width: 58, height: 58)
                                .overlay {
                                    Text("C")
                                        .font(.title2.weight(.black))
                                        .foregroundStyle(HDTheme.blue)
                                }
                            VStack(alignment: .leading, spacing: 3) {
                                Text("Chethan")
                                    .font(.title3.weight(.black))
                                Text("Private administrator")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            Spacer()
                        }
                        .hdCard()

                        VStack(spacing: 0) {
                            NavigationLink {
                                AnalyticsView()
                            } label: {
                                MoreRow(icon: "chart.bar.fill", title: "Website Analytics", color: HDTheme.blue)
                            }
                            Divider().padding(.leading, 48)
                            NavigationLink {
                                AutomationDetailsView()
                            } label: {
                                MoreRow(icon: "bolt.horizontal.circle.fill", title: "Publishing Automation", color: HDTheme.green)
                            }
                            Divider().padding(.leading, 48)
                            if let adminURL = URL(string: "https://hdcareers.in/admin/") {
                                Link(destination: adminURL) {
                                    MoreRow(icon: "safari.fill", title: "Open Web Admin", color: .purple)
                                }
                            }
                            Divider().padding(.leading, 48)
                            if let site = URL(string: "https://hdcareers.in") {
                                Link(destination: site) {
                                    MoreRow(icon: "globe", title: "Open HD Careers", color: HDTheme.blue)
                                }
                            }
                        }
                        .hdCard(0)

                        if CredentialVault.load() != nil {
                            Button(role: .destructive) {
                                state.removeSavedFaceID()
                            } label: {
                                Label("Remove saved Face ID login", systemImage: "faceid")
                                    .fontWeight(.semibold)
                                    .frame(maxWidth: .infinity)
                                    .padding(.vertical, 13)
                            }
                            .buttonStyle(.bordered)
                        }

                        Button(role: .destructive) {
                            Task { await state.logout() }
                        } label: {
                            Label("Sign Out", systemImage: "rectangle.portrait.and.arrow.right")
                                .fontWeight(.bold)
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 13)
                        }
                        .buttonStyle(.bordered)
                    }
                    .padding(16)
                }
            }
            .toolbar(.hidden, for: .navigationBar)
        }
    }
}

struct MoreRow: View {
    let icon: String
    let title: String
    let color: Color

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .foregroundStyle(color)
                .frame(width: 26)
            Text(title)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(HDTheme.navy)
            Spacer()
            Image(systemName: "chevron.right")
                .font(.caption.weight(.bold))
                .foregroundStyle(.tertiary)
        }
        .padding(15)
        .contentShape(Rectangle())
    }
}

struct AnalyticsView: View {
    @EnvironmentObject private var state: AppState

    var body: some View {
        ZStack {
            HDTheme.background.ignoresSafeArea()

            ScrollView {
                VStack(spacing: 14) {
                    Picker("Period", selection: Binding(
                        get: { state.trafficDays },
                        set: { days in Task { await state.loadTraffic(days: days) } }
                    )) {
                        Text("24H").tag(1)
                        Text("7D").tag(7)
                        Text("30D").tag(30)
                    }
                    .pickerStyle(.segmented)

                    HStack(spacing: 10) {
                        SmallMetric(title: "Live now", value: state.traffic?.realtimeUsers ?? 0, color: HDTheme.green)
                        SmallMetric(title: "Users", value: state.traffic?.totals?.visitors ?? 0, color: HDTheme.blue)
                        SmallMetric(title: "Views", value: state.traffic?.totals?.pageviews ?? 0, color: .purple)
                    }
                    .hdCard(10)

                    ConversionSummaryCard()

                    AnalyticsListCard(
                        title: "Top Apply Jobs",
                        icon: "arrow.up.right.square.fill",
                        rows: (state.traffic?.applyJobs ?? []).map {
                            (jobDisplayName(path: $0.requestPath, jobs: state.jobs), $0.count ?? 0)
                        }
                    )

                    AnalyticsListCard(
                        title: "Resume Checker Usage",
                        icon: "doc.text.magnifyingglass",
                        rows: (state.traffic?.resumeJobs ?? []).map {
                            (jobDisplayName(path: $0.requestPath, jobs: state.jobs), $0.count ?? 0)
                        }
                    )

                    AnalyticsListCard(
                        title: "Apply Conversion Sources",
                        icon: "point.3.connected.trianglepath.dotted",
                        rows: (state.traffic?.applySources ?? []).map {
                            (($0.referrerHostname?.isEmpty == false ? $0.referrerHostname! : "Direct / Unknown"), $0.count ?? 0)
                        }
                    )

                    AnalyticsListCard(
                        title: "Top Pages",
                        icon: "doc.text.fill",
                        rows: (state.traffic?.pages ?? []).map {
                            (jobDisplayName(path: $0.requestPath, jobs: state.jobs), $0.pageviews ?? 0)
                        }
                    )

                    AnalyticsListCard(
                        title: "Traffic Sources",
                        icon: "arrow.up.right.square.fill",
                        rows: (state.traffic?.referrers ?? []).map {
                            (($0.referrerHostname?.isEmpty == false ? $0.referrerHostname! : "Direct / Unknown"), $0.sessions ?? 0)
                        }
                    )

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
                .padding(16)
            }
        }
        .navigationTitle("Analytics")
        .navigationBarTitleDisplayMode(.inline)
    }
}

struct ConversionSummaryCard: View {
    @EnvironmentObject private var state: AppState

    private var conversions: TrafficResponse.Conversions? { state.traffic?.conversions }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Conversion Funnel")
                        .font(.headline.weight(.black))
                    Text("Job views → resume checks → official apply clicks")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Text(String(format: "%.1f%%", conversions?.applyRate ?? 0))
                    .font(.title3.weight(.black))
                    .foregroundStyle(.purple)
            }

            HStack(spacing: 10) {
                SmallMetric(title: "Job views", value: conversions?.jobPageViews ?? 0, color: .indigo)
                SmallMetric(title: "Resume checks", value: conversions?.resumeChecks ?? 0, color: .cyan)
                SmallMetric(title: "Apply clicks", value: conversions?.applyClicks ?? 0, color: HDTheme.green)
            }

            HStack(spacing: 10) {
                SmallMetric(title: "Apply users", value: conversions?.applyUsers ?? 0, color: HDTheme.green)
                SmallMetric(title: "Shares", value: conversions?.shares ?? 0, color: .orange)
                SmallMetric(title: "Social clicks", value: conversions?.socialClicks ?? 0, color: .pink)
            }

            Text("Conversion events accumulate from the analytics release onward.")
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .hdCard()
    }
}

struct AnalyticsListCard: View {
    let title: String
    let icon: String
    let rows: [(String, Int)]

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label(title, systemImage: icon)
                .font(.headline.weight(.black))

            if rows.isEmpty {
                Text("No data for this period.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            } else {
                ForEach(Array(rows.enumerated()), id: \.offset) { index, row in
                    HStack(alignment: .top) {
                        Text("\(index + 1)")
                            .font(.caption.weight(.black))
                            .foregroundStyle(HDTheme.blue)
                            .frame(width: 22, height: 22)
                            .background(HDTheme.blue.opacity(0.08))
                            .clipShape(Circle())
                        Text(row.0)
                            .font(.subheadline.weight(.semibold))
                            .lineLimit(2)
                        Spacer()
                        Text(numberText(row.1))
                            .font(.subheadline.weight(.black))
                    }
                    if index != rows.count - 1 {
                        Divider()
                    }
                }
            }
        }
        .hdCard()
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
