import styles from "./landing.module.css";

/**
 * Right-column animation on the landing page. Two-column "paper" card:
 *
 *   LEFT  — a stylized invoice with a scanning beam that crosses
 *           top-to-bottom on a 9s loop, plus five highlight boxes that
 *           fade in sequentially (Vendor → Invoice # → VAT ID → Line
 *           items → Total) as if the model were detecting them.
 *   RIGHT — the corresponding extracted data appearing as a list of
 *           field rows, each fading in (with a brief yellow flash) on
 *           the same 9s loop staggered to land just after the matching
 *           highlight on the left.
 *
 * Bottom footer is the "Export" pipeline with XLSX / CSV / JSON tiles
 * and a flowing dot along a thin rail.
 *
 * Pure CSS — no client JS, no state — so SSR matches the client.
 */
export function LiveExtractionStage() {
  return (
    <div className="relative w-full isolate">
      <div className={styles.paper}>
        <div className={styles.paperBody}>
          {/* LEFT: invoice with scanning highlights */}
          <div className={`${styles.col} ${styles.colLeft}`}>
            <div className={styles.colHead}>
              <span className={styles.label}>
                <span className={styles.num}>1</span> Source · PDF invoice
              </span>
              <span>PDF · 1 of 1</span>
            </div>

            <div className={styles.invoice}>
              <div className={styles.invoiceTop}>
                <div className={styles.vendor}>
                  Vertex Logistics LLC
                  <span className={styles.vendorGe}>ვერტექს ლოჯისტიქს</span>
                </div>
                <div className={styles.invoiceMeta}>
                  <div>INV-2026-01482</div>
                  <div>12 May 2026</div>
                </div>
              </div>
              <hr />
              <div className={styles.rowMeta}>
                <div>
                  <span className="k">VAT ID</span>
                  <span className="v">GE 405998721</span>
                </div>
                <div>
                  <span className="k">Currency</span>
                  <span className="v">GEL</span>
                </div>
              </div>
              <table className={styles.invoiceTable}>
                <thead>
                  <tr>
                    <th>Description</th>
                    <th>Qty</th>
                    <th>Amount</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>სარეკლამო კამპანია</td>
                    <td>1</td>
                    <td>1,850.00</td>
                  </tr>
                  <tr>
                    <td>საიტის მომსახურება</td>
                    <td>1</td>
                    <td>420.00</td>
                  </tr>
                  <tr>
                    <td>სასწავლო მომსახურებები</td>
                    <td>2</td>
                    <td>180.00</td>
                  </tr>
                  <tr>
                    <td>VAT 18%</td>
                    <td>—</td>
                    <td>441.00</td>
                  </tr>
                </tbody>
              </table>
              <div className={styles.totals}>
                <div>Subtotal  2,450.00 GEL</div>
                <div className={styles.totalsGrand}>2,891.00 ₾</div>
              </div>

              <div className={styles.stamp}>
                PDF
                <br />
                2026
              </div>

              {/* Highlights flash over the invoice as fields are detected */}
              <div className={`${styles.hl} ${styles.hlVendor}`} data-label="Vendor" />
              <div className={`${styles.hl} ${styles.hlInvoice}`} data-label="Invoice #" />
              <div className={`${styles.hl} ${styles.hlVat}`} data-label="VAT ID" />
              <div className={`${styles.hl} ${styles.hlLines}`} data-label="Line items" />
              <div className={`${styles.hl} ${styles.hlTotal}`} data-label="Total" />

              <div className={styles.scanbeam} />
            </div>
          </div>

          {/* RIGHT: extracted data appearing field-by-field */}
          <div className={`${styles.col} ${styles.colRight}`}>
            <div className={styles.colHead}>
              <span className={styles.label}>
                <span className={styles.num}>2</span> Extracted data
              </span>
              <span style={{ color: "var(--color-accent-2)", fontWeight: 500 }}>
                99.4% conf.
              </span>
            </div>

            <div className={styles.extract}>
              <div className={styles.field}>
                <span className="k">Vendor</span>
                <span className="v vGeo">ვერტექს ლოჯისტიქს</span>
                <span className="conf">100%</span>
              </div>
              <div className={styles.field}>
                <span className="k">Vendor (en)</span>
                <span className="v">Vertex Logistics LLC</span>
                <span className="conf">99%</span>
              </div>
              <div className={styles.field}>
                <span className="k">VAT ID</span>
                <span className="v">GE405998721</span>
                <span className="conf">100%</span>
              </div>
              <div className={styles.field}>
                <span className="k">Invoice №</span>
                <span className="v">INV-2026-01482</span>
                <span className="conf">100%</span>
              </div>
              <div className={styles.field}>
                <span className="k">Issued</span>
                <span className="v">2026-05-12</span>
                <span className="conf">99%</span>
              </div>
              <div className={styles.field}>
                <span className="k">Subtotal</span>
                <span className="v vAmt">2,450.00 GEL</span>
                <span className="conf">100%</span>
              </div>
              <div className={styles.field}>
                <span className="k">VAT (18%)</span>
                <span className="v vAmt">441.00 GEL</span>
                <span className="conf">100%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer: destinations pipeline */}
        <div className={styles.destinations}>
          <div className={styles.from}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round">
              <path d="M4 12h16M14 6l6 6-6 6" />
            </svg>
            <b>Export</b>
          </div>
          <div className={styles.pipe} />
          <div className={styles.dest}>
            <div className={`${styles.destLogo} ${styles.destXls}`} />
            <div>
              <div className={styles.destName}>Excel</div>
              <div className={styles.destStatus}>.xlsx</div>
            </div>
          </div>
          <div className={styles.dest}>
            <div className={`${styles.destLogo} ${styles.destCsv}`} />
            <div>
              <div className={styles.destName}>CSV</div>
              <div className={styles.destStatus}>.csv</div>
            </div>
          </div>
          <div className={styles.dest}>
            <div className={`${styles.destLogo} ${styles.destJson}`} />
            <div>
              <div className={styles.destName}>JSON</div>
              <div className={styles.destStatus}>.json</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
