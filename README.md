# HD Careers (hdcareers.in)

A single-page, mobile-first job & internship alert website for India — built with HTML, Tailwind CSS (CDN) and vanilla JavaScript. No build step, no backend required.

## Features
- Job listings with category filters (IT & Software, Internships, Off-Campus, Remote, Walk-in Drives) and live search
- Job details modal with eligibility, responsibilities, perks, and application steps
- Full "About" page view
- WhatsApp / Instagram / Telegram channel links
- Built-in WhatsApp channel post generator (admin utility)
- Google AdSense-ready placeholder banner slots
- Legal modals: Privacy Policy, Disclaimer, Contact Us

## Deploying on GitHub Pages
1. Create a new GitHub repository and upload the contents of this folder (just `index.html`) to it.
2. Go to **Settings → Pages** in your repository.
3. Under "Build and deployment", set **Source** to `Deploy from a branch`, choose the `main` branch and `/ (root)` folder, then **Save**.
4. GitHub will publish your site at `https://<your-username>.github.io/<repo-name>/` within a minute or two.
5. To use your own domain (hdcareers.in), add a `CNAME` file with your domain name to the repo root and configure your domain's DNS as per [GitHub's custom domain docs](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site).

## Editing
Everything — markup, styles and logic — lives in the single `index.html` file:
- Job data is in the `JOBS` array near the bottom of the file — edit, add, or remove entries there.
- Social links are set as plain `<a href="...">` tags — search for `whatsapp.com`, `instagram.com`, `t.me` to update them.
- Colors are defined as CSS variables at the top of the `<style>` block (`--primary`, `--dark`, `--slate`).

## Notes
- Replace the AdSense placeholder blocks (marked `ad-slot`) with your real AdSense `<ins>` code once your account is approved.
- Company "logos" are colored initials since no external images are embedded except your HD Careers logo (already embedded as base64).
