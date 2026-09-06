import { AccessPortal } from "@/components/access-portal";

import styles from "./page.module.css";

export default function Home() {
  return (
    <main id="main-content" className={styles.page}>
      <section className={styles.hero} aria-labelledby="page-title">
        <p className={styles.eyebrow}>Modernization workspace</p>
        <h1 id="page-title">A calmer way to run the library.</h1>
        <p className={styles.lead}>
          Discover books, manage borrowing, and keep every library workflow in one clear,
          welcoming place.
        </p>
        <div className={styles.accessGrid}>
          <div className={styles.promise}>
            <p>Built for members and library teams</p>
            <ul>
              <li>Browse availability without waiting on page navigation.</li>
              <li>Track loans, reservations, fines, requests, and feedback.</li>
              <li>Use one secure workspace for circulation and administration.</li>
            </ul>
          </div>
          <AccessPortal />
        </div>
      </section>

      <section className={styles.architecture} aria-labelledby="architecture-title">
        <div>
          <p className={styles.sectionLabel}>Designed around the work</p>
          <h2 id="architecture-title">Everything important stays close</h2>
        </div>
        <div className={styles.cards}>
          <article>
            <span>01</span>
            <h3>Find</h3>
            <p>Search the catalog and see physical-copy availability at a glance.</p>
          </article>
          <article>
            <span>02</span>
            <h3>Borrow</h3>
            <p>Keep reservations, loans, renewals, and account charges understandable.</p>
          </article>
          <article>
            <span>03</span>
            <h3>Operate</h3>
            <p>Give staff focused tools without exposing infrastructure or credentials.</p>
          </article>
        </div>
      </section>
    </main>
  );
}
