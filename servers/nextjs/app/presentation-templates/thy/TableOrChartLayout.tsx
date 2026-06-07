import React from "react"
import * as z from "zod"

const layoutId = "THYTableOrChartLayout"
const layoutName = "THY Data Table"
const layoutDescription = "Turkish Airlines branded data table slide with sortable columns"

const ColumnSchema = z
  .object({
    key: z.string().min(1).max(20).default("col1"),
    header: z.string().min(1).max(24).default("Column"),
    align: z.enum(["left", "center", "right"]).default("left"),
  })
  .default({ key: "col1", header: "Column", align: "left" })

const RowSchema = z
  .object({
    cells: z.array(z.string().max(60)).min(1).max(8).default(["Data"]),
  })
  .default({ cells: ["Data"] })

const Schema = z
  .object({
    title: z.string().min(4).max(52).default("Quarterly Performance"),
    description: z
      .string()
      .min(10)
      .max(180)
      .default("Overview of key performance indicators across business units."),
    columns: z
      .array(ColumnSchema)
      .min(1)
      .max(6)
      .default([
        ColumnSchema.parse({ key: "metric", header: "Metric", align: "left" }),
        ColumnSchema.parse({ key: "q1", header: "Q1 2025", align: "center" }),
        ColumnSchema.parse({ key: "q2", header: "Q2 2025", align: "center" }),
        ColumnSchema.parse({ key: "q3", header: "Q3 2025", align: "center" }),
        ColumnSchema.parse({ key: "ytd", header: "YTD", align: "right" }),
      ]),
    rows: z
      .array(RowSchema)
      .min(1)
      .max(8)
      .default([
        RowSchema.parse({ cells: ["Revenue (M TL)", "8,240", "9,150", "9,870", "27,260"] }),
        RowSchema.parse({ cells: ["EBITDA (M TL)", "2,472", "2,836", "3,012", "8,320"] }),
        RowSchema.parse({ cells: ["Passengers", "3.1M", "3.8M", "4.2M", "11.1M"] }),
        RowSchema.parse({ cells: ["Load Factor", "86.2%", "89.4%", "91.1%", "88.9%"] }),
        RowSchema.parse({ cells: ["Fleet Size", "315", "322", "328", "328"] }),
        RowSchema.parse({ cells: ["Destinations", "334", "338", "342", "342"] }),
        RowSchema.parse({ cells: ["On-Time %", "97.2%", "98.1%", "98.7%", "98.0%"] }),
      ]),
  })
  .default({
    title: "Quarterly Performance",
    description: "Overview of key performance indicators across business units.",
    columns: [
      ColumnSchema.parse({ key: "metric", header: "Metric", align: "left" }),
      ColumnSchema.parse({ key: "q1", header: "Q1 2025", align: "center" }),
      ColumnSchema.parse({ key: "q2", header: "Q2 2025", align: "center" }),
      ColumnSchema.parse({ key: "q3", header: "Q3 2025", align: "center" }),
      ColumnSchema.parse({ key: "ytd", header: "YTD", align: "right" }),
    ],
    rows: [
      RowSchema.parse({ cells: ["Revenue (M TL)", "8,240", "9,150", "9,870", "27,260"] }),
      RowSchema.parse({ cells: ["EBITDA (M TL)", "2,472", "2,836", "3,012", "8,320"] }),
      RowSchema.parse({ cells: ["Passengers", "3.1M", "3.8M", "4.2M", "11.1M"] }),
      RowSchema.parse({ cells: ["Load Factor", "86.2%", "89.4%", "91.1%", "88.9%"] }),
      RowSchema.parse({ cells: ["Fleet Size", "315", "322", "328", "328"] }),
      RowSchema.parse({ cells: ["Destinations", "334", "338", "342", "342"] }),
      RowSchema.parse({ cells: ["On-Time %", "97.2%", "98.1%", "98.7%", "98.0%"] }),
    ],
  })

type SlideData = z.infer<typeof Schema>

interface SlideLayoutProps {
  data?: Partial<SlideData>
}

const THYTableOrChartLayout: React.FC<SlideLayoutProps> = ({ data: slideData }) => {
  const columns = slideData?.columns || []
  const rows = slideData?.rows || []

  const getAlignStyle = (align: string) => {
    switch (align) {
      case "center":
        return "center" as const
      case "right":
        return "right" as const
      default:
        return "left" as const
    }
  }

  return (
    <>
      <link
        href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&family=Inter:wght@400;500;600&display=swap"
        rel="stylesheet"
      />

      <div
        className="w-full rounded-sm max-w-[1280px] shadow-lg max-h-[720px] aspect-video relative z-20 mx-auto overflow-hidden"
        style={{
          fontFamily: "var(--heading-font-family, Montserrat)",
          backgroundColor: "var(--background-color, #FFFFFF)",
        }}
      >
        {/* Top accent stripe */}
        <div className="absolute top-0 left-0 right-0 h-[6px]" style={{ backgroundColor: "var(--primary-color, #E8192D)" }}></div>

        {/* Header */}
        <div className="px-14 pt-10 pb-2">
          <div className="flex items-center gap-3">
            {(slideData as any)?._logo_url__ && (
              <img src={(slideData as any)?._logo_url__} alt="logo" className="h-8" />
            )}
            {(slideData as any)?.__companyName__ && (
              <span
                className="text-[13px] tracking-[0.2em] uppercase font-semibold"
                style={{ color: "var(--background-text, #00205B)" }}
              >
                {(slideData as any)?.__companyName__}
              </span>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="px-14 pt-6">
          <div
            className="inline-block mb-4 w-10 h-[3px] rounded-full"
            style={{ backgroundColor: "var(--primary-color, #E8192D)" }}
          ></div>
          <h1
            className="text-[38px] leading-[1.1] font-bold"
            style={{ color: "var(--background-text, #00205B)" }}
          >
            {slideData?.title}
          </h1>
          <p
            className="mt-2 text-[14px] leading-[1.5] max-w-[700px]"
            style={{ color: "var(--background-text, #64748B)", fontFamily: "var(--body-font-family, Inter)" }}
          >
            {slideData?.description}
          </p>

          {/* Table */}
          <div className="mt-6 rounded-xl overflow-hidden border" style={{ borderColor: "var(--background-text, #E2E8F0)" }}>
            <table className="w-full">
              <thead>
                <tr style={{ backgroundColor: "var(--primary-color, #E8192D)" }}>
                  {columns.map((col, i) => (
                    <th
                      key={i}
                      className="px-5 py-3 text-[13px] font-semibold tracking-wide uppercase"
                      style={{
                        color: "var(--primary-text, #FFFFFF)",
                        textAlign: getAlignStyle(col.align || "left"),
                        borderRight:
                          i < columns.length - 1
                            ? "1px solid rgba(255,255,255,0.2)"
                            : "none",
                      }}
                    >
                      {col.header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row, ri) => (
                  <tr
                    key={ri}
                    style={{
                      backgroundColor:
                        ri % 2 === 0
                          ? "var(--background-color, #FFFFFF)"
                          : "var(--background-color, #F8FAFC)",
                    }}
                  >
                    {row.cells.map((cell, ci) => (
                      <td
                        key={ci}
                        className={`px-5 py-3 text-[13px] ${ci === 0 ? "font-semibold" : ""}`}
                        style={{
                          color: ci === 0 ? "var(--background-text, #00205B)" : "var(--background-text, #475569)",
                          fontFamily: ci === 0 ? "undefined" : "var(--body-font-family, Inter)",
                          textAlign: getAlignStyle(columns[ci]?.align || "left"),
                          borderRight:
                            ci < row.cells.length - 1
                              ? "1px solid var(--background-text, #E2E8F0)"
                              : "none",
                          borderBottom:
                            ri < rows.length - 1
                              ? "1px solid var(--background-text, #E2E8F0)"
                              : "none",
                        }}
                      >
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="absolute bottom-0 left-0 right-0 h-[6px]" style={{ backgroundColor: "var(--primary-color, #E8192D)" }}></div>
        <div className="absolute bottom-6 left-14 right-14 flex items-center gap-4">
          <span
            className="text-[12px] tracking-wide uppercase font-medium"
            style={{ color: "var(--background-text, #00205B)" }}
          >
            Turkish Airlines
          </span>
          <div className="h-[1px] flex-1" style={{ backgroundColor: "var(--background-text, #E2E8F0)", opacity: 0.4 }}></div>
          <span
            className="text-[12px] tracking-wide"
            style={{ color: "var(--background-text, #94A3B8)" }}
          >
            turkishairlines.com
          </span>
        </div>
      </div>
    </>
  )
}

export { Schema, layoutId, layoutName, layoutDescription }
export default THYTableOrChartLayout
