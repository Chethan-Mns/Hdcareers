import SwiftUI

@main
struct HDCareersAdminApp: App {
    var body: some Scene {
        WindowGroup {
            ZStack {
                Color.white.ignoresSafeArea()

                VStack(spacing: 18) {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.system(size: 64, weight: .bold))
                        .foregroundStyle(.green)

                    Text("HD Careers Admin")
                        .font(.system(size: 28, weight: .black, design: .rounded))
                        .foregroundStyle(.black)

                    Text("App Loaded")
                        .font(.title3.weight(.bold))
                        .foregroundStyle(.blue)

                    Text("No API • No Analytics • No Login")
                        .font(.footnote.weight(.semibold))
                        .foregroundStyle(.secondary)
                }
                .padding(24)
            }
            .preferredColorScheme(.light)
        }
    }
}
