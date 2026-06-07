import React from "react"
import * as z from "zod"

const layoutId = "THYBulletPointsLayout"
const layoutName = "THY Bullet Points"
const layoutDescription = "Turkish Airlines branded content slide with title, body and bullet points"

const PointSchema = z
  .object({
    title: z.string().min(4).max(52).default("Key Initiative"),
    body: z
      .string()
      .min(20)
      .max(200)
      .default(
        "Driving operational excellence through digital transformation and continuous improvement across all touchpoints."
      ),
  })
  .default({
    title: "Key Initiative",
    body: "Driving operational excellence through digital transformation and continuous improvement across all touchpoints.",
  })

const Schema = z
  .object({
    title: z.string().min(6).max(52).default("Our Strategic Priorities"),
    description: z
      .string()
      .min(20)
      .max(240)
      .default(
        "We focus on delivering exceptional experiences while maintaining operational excellence and sustainable growth."
      ),
    points: z
      .array(PointSchema)
      .min(1)
      .max(4)
      .default([
        PointSchema.parse({ title: "Global Connectivity", body: "Expanding our network to connect more destinations with seamless travel experiences worldwide." }),
        PointSchema.parse({ title: "Service Excellence", body: "Delivering award-winning hospitality and comfort at every stage of the passenger journey." }),
        PointSchema.parse({ title: "Digital Innovation", body: "Leveraging cutting-edge technology to enhance booking, check-in and in-flight experiences." }),
        PointSchema.parse({ title: "Sustainability", body: "Committing to carbon-neutral growth and eco-friendly operations across our entire fleet." }),
      ]),
  })
  .default({
    title: "Our Strategic Priorities",
    description:
      "We focus on delivering exceptional experiences while maintaining operational excellence and sustainable growth.",
    points: [
      PointSchema.parse({ title: "Global Connectivity", body: "Expanding our network to connect more destinations with seamless travel experiences worldwide." }),
      PointSchema.parse({ title: "Service Excellence", body: "Delivering award-winning hospitality and comfort at every stage of the passenger journey." }),
      PointSchema.parse({ title: "Digital Innovation", body: "Leveraging cutting-edge technology to enhance booking, check-in and in-flight experiences." }),
      PointSchema.parse({ title: "Sustainability", body: "Committing to carbon-neutral growth and eco-friendly operations across our entire fleet." }),
    ],
  })

type SlideData = z.infer<typeof Schema>

interface SlideLayoutProps {
  data?: Partial<SlideData>
}

const THYBulletPointsLayout: React.FC<SlideLayoutProps> = ({ data: slideData }) => {
  const points = slideData?.points || []
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
        <div className="grid grid-cols-[44%_56%] gap-12 px-14 pt-8 items-start">
          {/* Left: title and description */}
          <div>
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
              className="mt-5 text-[16px] leading-[1.7]"
              style={{ color: "var(--background-text, #64748B)", fontFamily: "var(--body-font-family, Inter)" }}
            >
              {slideData?.description}
            </p>
          </div>

          {/* Right: bullet points */}
          <div className="flex flex-col gap-6">
            {points.slice(0, 4).map((p, i) => (
              <div key={i} className="flex gap-4">
                {/* Number circle */}
                <div
                  className="flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center text-[14px] font-bold"
                  style={{
                    backgroundColor: "var(--primary-color, #E8192D)",
                    color: "var(--primary-text, #FFFFFF)",
                  }}
                >
                  {String(i + 1).padStart(2, "0")}
                </div>
                <div className="pt-0.5">
                  <div
                    className="text-[18px] font-semibold"
                    style={{ color: "var(--background-text, #00205B)" }}
                  >
                    {p.title}
                  </div>
                  <p
                    className="mt-1.5 text-[14px] leading-[1.65]"
                    style={{ color: "var(--background-text, #64748B)", fontFamily: "var(--body-font-family, Inter)" }}
                  >
                    {p.body}
                  </p>
                </div>
              </div>
            ))}
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
export default THYBulletPointsLayout
