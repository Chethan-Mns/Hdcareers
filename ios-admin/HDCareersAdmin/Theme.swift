import SwiftUI

enum HDTheme {
    static let blue = Color(red: 0.035, green: 0.412, blue: 0.855)
    static let navy = Color(red: 0.027, green: 0.102, blue: 0.200)
    static let background = Color(red: 0.965, green: 0.976, blue: 0.992)
    static let green = Color(red: 0.086, green: 0.639, blue: 0.290)
    static let amber = Color(red: 0.957, green: 0.620, blue: 0.035)
    static let red = Color(red: 0.862, green: 0.149, blue: 0.149)
}

struct HDCard: ViewModifier {
    var padding: CGFloat = 16

    func body(content: Content) -> some View {
        content
            .padding(padding)
            .background(.white)
            .clipShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: 20, style: .continuous)
                    .stroke(Color.black.opacity(0.06), lineWidth: 1)
            }
            .shadow(color: .black.opacity(0.045), radius: 14, y: 6)
    }
}

extension View {
    func hdCard(_ padding: CGFloat = 16) -> some View {
        modifier(HDCard(padding: padding))
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
                    .stroke(Color.black.opacity(0.06))
            }
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
        .font(.caption2.weight(.bold))
        .foregroundStyle(color)
        .padding(.horizontal, 9)
        .padding(.vertical, 6)
        .background(color.opacity(0.10))
        .clipShape(Capsule())
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

    private var remoteURL: URL? {
        if let raw = job.logoUrl?.trimmingCharacters(in: .whitespacesAndNewlines),
           !raw.isEmpty,
           let url = URL(string: raw) {
            return url
        }

        if let company = job.company, let direct = directLogos[company] {
            return URL(string: direct)
        }

        let company = job.company ?? ""
        var domain = companyDomains[company] ?? job.domain ?? ""
        domain = domain
            .replacingOccurrences(of: "https://", with: "")
            .replacingOccurrences(of: "http://", with: "")
            .split(separator: "/")
            .first
            .map(String.init) ?? ""

        guard !domain.isEmpty else { return nil }
        let encoded = ("https://" + domain).addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? domain
        return URL(string: "https://www.google.com/s2/favicons?domain_url=\(encoded)&sz=256")
    }

    var body: some View {
        Group {
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
                default:
                    fallback
                }
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

    private var fallback: some View {
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
