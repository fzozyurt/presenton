import React from "react"
import * as z from "zod"

const layoutId = "THYMetricsLayout"
const layoutName = "THY Metrics Dashboard"
const layoutDescription = "Turkish Airlines branded KPI slide with metric cards and supporting text"

const MetricSchema = z
  .object({
    value: z.string().min(1).max(12).default("12.4M"),
    label: z.string().min(2).max(28).default("Passengers"),
    change: z.string().min(1).max(8).default("+8.2%"),
    positive: z.boolean().default(true),
  })
  .default({
    value: "12.4M",
    label: "Passengers",
    change: "+8.2%",
    positive: true,
  })

const Schema = z
  .object({
    title: z
      .string()
      .min(6)
      .max(52)
      .default("Performance at a Glance"),
    subtitle: z
      .string()
      .min(10)
      .max(160)
      .default(
        "Key operational metrics demonstrating our continued growth and market leadership position."
      ),
    metrics: z
      .array(MetricSchema)
      .min(2)
      .max(4)
      .default([
        MetricSchema.parse({ value: "12.4M", label: "Passengers", change: "+8.2%", positive: true }),
        MetricSchema.parse({ value: "342", label: "Destinations", change: "+26", positive: true }),
        MetricSchema.parse({ value: "89.2%", label: "Load Factor", change: "+1.8%", positive: true }),
        MetricSchema.parse({ value: "98.7%", label: "On-Time Perf.", change: "+0.5%", positive: true }),
      ]),
  })
  .default({
    title: "Performance at a Glance",
    subtitle:
      "Key operational metrics demonstrating our continued growth and market leadership position.",
    metrics: [
      MetricSchema.parse({ value: "12.4M", label: "Passengers", change: "+8.2%", positive: true }),
      MetricSchema.parse({ value: "342", label: "Destinations", change: "+26", positive: true }),
      MetricSchema.parse({ value: "89.2%", label: "Load Factor", change: "+1.8%", positive: true }),
      MetricSchema.parse({ value: "98.7%", label: "On-Time Perf.", change: "+0.5%", positive: true }),
    ],
  })

type SlideData = z.infer<typeof Schema>

interface SlideLayoutProps {
  data?: Partial<SlideData>
}

const THYMetricsLayout: React.FC<SlideLayoutProps> = ({ data: slideData }) => {
  const metrics = slideData?.metrics || []
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
        <div className="px-14 pt-8">
          <div
            className="inline-block mb-5 w-10 h-[3px] rounded-full"
            style={{ backgroundColor: "var(--primary-color, #E8192D)" }}
          ></div>
          <h1
            className="text-[44px] leading-[1.1] font-bold"
            style={{ color: "var(--background-text, #00205B)" }}
          >
            {slideData?.title}
          </h1>
          <p
            className="mt-4 text-[16px] leading-[1.6] max-w-[720px]"
            style={{ color: "var(--background-text, #64748B)", fontFamily: "var(--body-font-family, Inter)" }}
          >
            {slideData?.subtitle}
          </p>

          {/* Metric cards */}
          <div className={`grid grid-cols-${Math.min(metrics.length, 4)} gap-5 mt-10 ${metrics.length === 4 ? "" : "max-w-[900px]"}`}>
            <div
              className="grid gap-5"
              style={{
                gridTemplateColumns: `repeat(${Math.min(metrics.length, 4)}, minmax(0, 1fr))`,
              }}
            >
              {metrics.slice(0, 4).map((m, i) => (
                <div
                  key={i}
                  className="rounded-xl p-6 relative overflow-hidden group"
                  style={{
                    backgroundColor: "var(--background-color, #F8FAFC)",
                    border: "1px solid",
                    borderColor: "var(--background-text, #E2E8F0)",
                    borderLeftWidth: "4px",
                    borderLeftColor: "var(--primary-color, #E8192D)",
                  }}
                >
                  {/* Metric value */}
                  <div
                    className="text-[38px] leading-[1.1] font-bold"
                    style={{ color: "var(--background-text, #00205B)" }}
                  >
                    {m.value}
                  </div>
                  {/* Metric label */}
                  <div
                    className="mt-2 text-[14px] font-medium"
                    style={{ color: "var(--background-text, #64748B)", fontFamily: "var(--body-font-family, Inter)" }}
                  >
                    {m.label}
                  </div>
                  {/* Change indicator */}
                  <div className="mt-3 flex items-center gap-1.5">
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 14 14"
                      fill="none"
                    >
                      {m.positive ? (
                        <path
                          d="M7 2L12 7L10.6 8.4L8 5.8V12H6V5.8L3.4 8.4L2 7L7 2Z"
                          fill="var(--success-color, #16A34A)"
                        />
                      ) : (
                        <path
                          d="M7 12L2 7L3.4 5.6L6 8.2V2H8V8.2L10.6 5.6L12 7L7 12Z"
                          fill="var(--primary-color, #E8192D)"
                        />
                      )}
                    </svg>
                    <span
                      className="text-[13px] font-semibold"
                      style={{
                        color: m.positive
                          ? "var(--success-color, #16A34A)"
                          : "var(--primary-color, #E8192D)",
                        fontFamily: "var(--body-font-family, Inter)",
                      }}
                    >
                      {m.change}
                    </span>
                    <span
                      className="text-[12px]"
                      style={{ color: "var(--background-text, #94A3B8)", fontFamily: "var(--body-font-family, Inter)" }}
                    >
                      YoY
                    </span>
                  </div>
                </div>
              ))}
            </div>
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
export default THYMetricsLayout
