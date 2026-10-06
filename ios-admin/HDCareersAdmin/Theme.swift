import SwiftUI

enum HDTheme {
    static let blue = Color(red: 0.055, green: 0.365, blue: 0.820)
    static let navy = Color(red: 0.035, green: 0.075, blue: 0.145)
    static let background = Color(red: 0.963, green: 0.968, blue: 0.978)
    static let green = Color(red: 0.055, green: 0.565, blue: 0.325)
    static let amber = Color(red: 0.875, green: 0.500, blue: 0.055)
    static let red = Color(red: 0.820, green: 0.155, blue: 0.180)
    static let violet = Color(red: 0.390, green: 0.285, blue: 0.820)
    static let cyan = Color(red: 0.035, green: 0.540, blue: 0.700)
    static let pink = Color(red: 0.820, green: 0.245, blue: 0.480)
    static let surface = Color.white
    static let softBlue = Color(red: 0.948, green: 0.963, blue: 0.990)
    static let border = Color.black.opacity(0.055)
    static let softShadow = Color(red: 0.03, green: 0.08, blue: 0.16).opacity(0.055)
}

struct HDCard: ViewModifier {
    var padding: CGFloat = 16

    func body(content: Content) -> some View {
        content
            .padding(padding)
            .background(HDTheme.surface)
            .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: 18, style: .continuous)
                    .stroke(HDTheme.border, lineWidth: 1)
            }
            .shadow(color: HDTheme.softShadow, radius: 10, x: 0, y: 4)
    }
}

extension View {
    func hdCard(_ padding: CGFloat = 16) -> some View {
        modifier(HDCard(padding: padding))
    }

    func premiumCard(_ padding: CGFloat = 16) -> some View {
        self
            .padding(padding)
            .background(HDTheme.surface)
            .clipShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: 20, style: .continuous)
                    .stroke(HDTheme.border, lineWidth: 1)
            }
            .shadow(color: HDTheme.softShadow, radius: 14, x: 0, y: 6)
    }
}

struct HDLogoView: View {
    var size: CGFloat = 48

    var body: some View {
        Image("HDLogo")
            .resizable()
            .scaledToFit()
            .frame(width: size, height: size)
            .background(.white)
            .clipShape(RoundedRectangle(cornerRadius: size * 0.22, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: size * 0.22, style: .continuous)
                    .stroke(HDTheme.border)
            }
            .shadow(color: HDTheme.softShadow, radius: 5, y: 2)
    }
}

struct StatusPill: View {
    let text: String
    let color: Color
    var icon: String? = nil

    var body: some View {
        HStack(spacing: 5) {
            if let icon {
                Image(systemName: icon)
            }
            Text(text)
        }
        .font(.system(size: 10, weight: .bold))
        .foregroundStyle(color)
        .padding(.horizontal, 9)
        .padding(.vertical, 5)
        .background(color.opacity(0.085))
        .clipShape(Capsule())
        .overlay {
            Capsule().stroke(color.opacity(0.10), lineWidth: 1)
        }
    }
}

struct EmptyState: View {
    let icon: String
    let title: String
    let message: String

    var body: some View {
        VStack(spacing: 10) {
            Image(systemName: icon)
                .font(.system(size: 28, weight: .semibold))
                .foregroundStyle(.secondary)
            Text(title)
                .font(.headline)
            Text(message)
                .font(.subheadline)
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 34)
    }
}


extension Color {
    init?(hex: String) {
        var value = hex.trimmingCharacters(in: .whitespacesAndNewlines)
        if value.hasPrefix("#") { value.removeFirst() }
        guard value.count == 6, let rgb = Int(value, radix: 16) else { return nil }
        self.init(
            red: Double((rgb >> 16) & 0xFF) / 255.0,
            green: Double((rgb >> 8) & 0xFF) / 255.0,
            blue: Double(rgb & 0xFF) / 255.0
        )
    }
}

struct CompanyLogoView: View {
    let job: Job
    var size: CGFloat = 46

    private let directLogos: [String: String] = [
        "DRDO – VRDE": "https://drdo.gov.in/drdo/sites/default/files/inline-images/logo_0.png",
        "DRDO – LRDE": "https://drdo.gov.in/drdo/sites/default/files/inline-images/logo_0.png",
        "DRDO – DYSL-SM": "https://drdo.gov.in/drdo/sites/default/files/inline-images/logo_0.png",
        "DRDO – Research Centre Imarat (RCI)": "https://drdo.gov.in/drdo/sites/default/files/inline-images/logo_0.png",
        "DRDO – Proof & Experimental Establishment (PXE)": "https://drdo.gov.in/drdo/sites/default/files/inline-images/logo_0.png",
        "Advanced Centre for Treatment, Research and Education in Cancer (ACTREC)": "https://actrec.gov.in/themes/actrec/images/SSA/Images/ACTREC_LOGO.png",
        "Electronics Corporation of India Limited (ECIL)": "https://www.ecil.co.in/images/ECIL_NewLogos2.png"
    ]

    private let companyDomains: [String: String] = [
        "Amazon.jobs": "amazon.com",
        "Amazon": "amazon.com",
        "IBM": "ibm.com",
        "PwC": "pwc.com",
        "PWC": "pwc.com",
        "Accenture": "accenture.com",
        "Infosys": "infosys.com",
        "Zoho": "zoho.com",
        "TCS": "tcs.com",
        "Wipro": "wipro.com",
        "Cognizant": "cognizant.com",
        "HCLTech": "hcltech.com",
        "Deloitte": "deloitte.com",
        "ISRO": "isro.gov.in",
        "Cohere Health": "coherehealth.com",
        "Hevo Data": "hevodata.com",
        "Qualcomm": "qualcomm.com",
        "SAP": "sap.com",
        "Priceline": "priceline.com",
        "Canonical": "canonical.com",
        "IndiGo": "goindigo.in"
    ]

    private var nativeBrand: String? {
        switch job.company {
        case "Amazon": return "amazon"
        case "Wipro": return "wipro"
        case "Deloitte": return "deloitte"
        case "Qualcomm": return "qualcomm"
        case "Advanced Centre for Treatment, Research and Education in Cancer (ACTREC)": return "actrec"
        case "Electronics Corporation of India Limited (ECIL)": return "ecil"
        case "Cochin Shipyard Limited", "Cochin Shipyard Limited – CMSRU": return "csl"
        default: return nil
        }
    }

    private var mark: String {
        if let logo = job.logo, let first = logo.first, !first.isEmpty {
            return first
        }
        let parts = (job.company ?? "HD").split(separator: " ")
        if parts.count >= 2 {
            return (String(parts[0].prefix(1)) + String(parts[1].prefix(1))).uppercased()
        }
        return String((job.company ?? "HD").prefix(2)).uppercased()
    }

    private var brandColor: Color {
        if let logo = job.logo, logo.count > 1, let color = Color(hex: logo[1]) {
            return color
        }
        return HDTheme.blue
    }

    private let genericRecruitingHosts = [
        "myworkdayjobs.com", "myworkdaysite.com", "greenhouse.io", "lever.co",
        "successfactors.com", "taleo.net", "oraclecloud.com", "icims.com",
        "smartrecruiters.com", "workable.com", "infosysapps.com"
    ]

    private func host(_ value: String?) -> String {
        guard let value, let url = URL(string: value), let host = url.host?.lowercased() else { return "" }
        return host.hasPrefix("www.") ? String(host.dropFirst(4)) : host
    }

    private func genericRecruitingHost(_ value: String?) -> Bool {
        let valueHost = host(value)
        return genericRecruitingHosts.contains { valueHost == $0 || valueHost.hasSuffix("." + $0) }
    }

    private var companyDomain: String {
        let company = job.company ?? ""
        var domain = companyDomains[company] ?? job.domain ?? ""
        domain = domain
            .replacingOccurrences(of: "https://", with: "")
            .replacingOccurrences(of: "http://", with: "")
            .split(separator: "/")
            .first
            .map(String.init) ?? ""
        if domain.hasPrefix("www.") { domain = String(domain.dropFirst(4)) }
        return domain.lowercased()
    }

    private var careerHostIsTrusted: Bool {
        let applyHost = host(job.apply)
        guard !applyHost.isEmpty, !genericRecruitingHost(job.apply) else { return false }
        if applyHost == "amazon.jobs" || applyHost.hasSuffix(".amazon.jobs") { return true }
        guard !companyDomain.isEmpty else { return true }
        return applyHost == companyDomain || applyHost.hasSuffix("." + companyDomain)
    }

    private var remoteURL: URL? {
        if let company = job.company, let direct = directLogos[company], let url = URL(string: direct) {
            return url
        }

        if careerHostIsTrusted,
           let raw = job.careerIconUrl?.trimmingCharacters(in: .whitespacesAndNewlines),
           raw.hasPrefix("https://"),
           let url = URL(string: raw) {
            return url
        }

        if !companyDomain.isEmpty {
            let encoded = ("https://" + companyDomain).addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? companyDomain
            if let url = URL(string: "https://www.google.com/s2/favicons?domain_url=\(encoded)&sz=256") {
                return url
            }
        }

        if careerHostIsTrusted,
           let apply = job.apply?.trimmingCharacters(in: .whitespacesAndNewlines),
           apply.hasPrefix("https://"),
           let encoded = apply.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed),
           let url = URL(string: "https://www.google.com/s2/favicons?domain_url=\(encoded)&sz=256") {
            return url
        }

        if let raw = job.logoUrl?.trimmingCharacters(in: .whitespacesAndNewlines),
           !raw.isEmpty,
           let url = URL(string: raw) {
            return url
        }

        return nil
    }

    var body: some View {
        Group {
            if nativeBrand != nil {
                fallback
            } else if let url = remoteURL {
                AsyncImage(url: url) { phase in
                    switch phase {
                    case .success(let image):
                        image
                            .resizable()
                            .scaledToFit()
                            .padding(2)
                    default:
                        fallback
                    }
                }
            } else {
                fallback
            }
        }
        .frame(width: size, height: size)
        .background(.white)
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .stroke(Color.black.opacity(0.06))
        }
    }

    @ViewBuilder
    private var fallback: some View {
        if let nativeBrand {
            switch nativeBrand {
            case "amazon":
                AmazonCompactMark()
            case "wipro":
                Text("wipro")
                    .font(.system(size: size * 0.28, weight: .bold, design: .rounded))
                    .foregroundStyle(Color(red: 0.42, green: 0.10, blue: 0.60))
            case "deloitte":
                HStack(alignment: .lastTextBaseline, spacing: 2) {
                    Text("D")
                        .font(.system(size: size * 0.58, weight: .black, design: .rounded))
                        .foregroundStyle(Color(red: 0.07, green: 0.09, blue: 0.12))
                    Circle()
                        .fill(Color(red: 0.53, green: 0.74, blue: 0.15))
                        .frame(width: size * 0.10, height: size * 0.10)
                }
            case "qualcomm":
                Text("Q")
                    .font(.system(size: size * 0.52, weight: .black, design: .rounded))
                    .foregroundStyle(Color(red: 0.20, green: 0.33, blue: 0.86))
            case "actrec":
                Text("ACTREC")
                    .font(.system(size: size * 0.19, weight: .black, design: .rounded))
                    .foregroundStyle(Color(red: 0.65, green: 0.12, blue: 0.24))
                    .minimumScaleFactor(0.7)
            case "ecil":
                Text("ECIL")
                    .font(.system(size: size * 0.26, weight: .black, design: .rounded))
                    .foregroundStyle(Color(red: 0.04, green: 0.37, blue: 0.66))
            case "csl":
                VStack(spacing: 1) {
                    Text("CSL")
                        .font(.system(size: size * 0.30, weight: .black, design: .rounded))
                        .foregroundStyle(Color(red: 0.09, green: 0.23, blue: 0.40))
                    Capsule()
                        .fill(Color(red: 0.95, green: 0.55, blue: 0.16))
                        .frame(width: size * 0.48, height: max(2, size * 0.07))
                }
            default:
                initialsFallback
            }
        } else {
            initialsFallback
        }
    }

    private var initialsFallback: some View {
        ZStack {
            brandColor.opacity(0.12)
            Text(mark)
                .font(.system(size: mark.count > 4 ? 9 : 12, weight: .black, design: .rounded))
                .foregroundStyle(brandColor)
                .minimumScaleFactor(0.6)
                .lineLimit(1)
                .padding(.horizontal, 4)
        }
    }

}

struct AmazonCompactMark: View {
    var body: some View {
        GeometryReader { geo in
            ZStack {
                Text("a")
                    .font(.system(size: geo.size.width * 0.62, weight: .bold, design: .rounded))
                    .foregroundStyle(Color(red: 0.07, green: 0.09, blue: 0.12))
                    .offset(y: -geo.size.height * 0.05)

                Path { p in
                    p.move(to: CGPoint(x: geo.size.width * 0.24, y: geo.size.height * 0.70))
                    p.addQuadCurve(
                        to: CGPoint(x: geo.size.width * 0.74, y: geo.size.height * 0.72),
                        control: CGPoint(x: geo.size.width * 0.50, y: geo.size.height * 0.84)
                    )
                }
                .stroke(Color(red: 1.0, green: 0.60, blue: 0.0), style: StrokeStyle(lineWidth: 3, lineCap: .round))

                Path { p in
                    p.move(to: CGPoint(x: geo.size.width * 0.68, y: geo.size.height * 0.67))
                    p.addLine(to: CGPoint(x: geo.size.width * 0.77, y: geo.size.height * 0.70))
                    p.addLine(to: CGPoint(x: geo.size.width * 0.72, y: geo.size.height * 0.78))
                }
                .stroke(Color(red: 1.0, green: 0.60, blue: 0.0), style: StrokeStyle(lineWidth: 3, lineCap: .round, lineJoin: .round))
            }
        }
    }
}
