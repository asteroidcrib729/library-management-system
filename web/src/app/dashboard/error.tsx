"use client";

export default function DashboardError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <main id="main-content" className="center-page"><div className="state-card state-card-error" role="alert"><div><strong>The dashboard encountered an unexpected problem</strong><p>Your session and saved library data have not been changed.</p></div><button className="button button-secondary" type="button" onClick={reset}>Try this view again</button></div></main>;
}
