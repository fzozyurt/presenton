import React from "react"
import * as z from "zod"

const layoutId = "THYTimelineLayout"
const layoutName = "THY Timeline"
const layoutDescription = "Turkish Airlines branded milestone timeline with 4-5 events"

const EventSchema = z
  .object({
    year: z.string().min(2).max(20).default("2025"),
    title: z.string().min(3).max(36).default("Milestone"),
    description: z
      .string()
      .min(10)
      .max(120)
      .default("Key achievement and progress update for this period."),
  })
  .default({
    year: "2025",
    title: "Milestone",
    description: "Key achievement and progress update for this period.",
  })

const Schema = z
  .object({
    title: z.string().min(6).max(52).default("Our Journey"),
    subtitle: z
      .string()
      .min(10)
      .max(140)
      .default("A timeline of milestones shaping our growth and industry leadership."),
    events: z
      .array(EventSchema)
      .min(3)
      .max(5)
      .default([
        EventSchema.parse({ year: "1933", title: "Founded", description: "Turkish Airlines established with a fleet of 5 aircraft, beginning domestic operations." }),
        EventSchema.parse({ year: "1956", title: "International Expansion", description: "First international routes launched, connecting Turkey to Europe and the Middle East." }),
        EventSchema.parse({ year: "2008", title: "Star Alliance", description: "Joined Star Alliance, the world's largest global airline alliance, expanding network reach." }),
        EventSchema.parse({ year: "2018", title: "New Istanbul Airport", description: "Relocated hub to the world-class Istanbul Airport, one of the largest aviation hubs globally." }),
        EventSchema.parse({ year: "2025", title: "Global Leader", description: "Operating 342 destinations across 129 countries with one of the youngest fleets in the world." }),
      ]),
  })
  .default({
    title: "Our Journey",
    subtitle: "A timeline of milestones shaping our growth and industry leadership.",
    events: [
      EventSchema.parse({ year: "1933", title: "Founded", description: "Turkish Airlines established with a fleet of 5 aircraft, beginning domestic operations." }),
      EventSchema.parse({ year: "1956", title: "International Expansion", description: "First international routes launched, connecting Turkey to Europe and the Middle East." }),
      EventSchema.parse({ year: "2008", title: "Star Alliance", description: "Joined Star Alliance, the world's largest global airline alliance, expanding network reach." }),
      EventSchema.parse({ year: "2018", title: "New Istanbul Airport", description: "Relocated hub to the world-class Istanbul Airport, one of the largest aviation hubs globally." }),
      EventSchema.parse({ year: "2025", title: "Global Leader", description: "Operating 342 destinations across 129 countries with one of the youngest fleets in the world." }),
    ],
  })

type SlideData = z.infer<typeof Schema>

interface SlideLayoutProps {
  data?: Partial<SlideData>
}

const THYTimelineLayout: React.FC<SlideLayoutProps> = ({ data: slideData }) => {
  const events = slideData?.events || []
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
            className="text-[44px] leading-[1.1] font-bold"
            style={{ color: "var(--background-text, #00205B)" }}
          >
            {slideData?.title}
          </h1>
          <p
            className="mt-3 text-[16px] leading-[1.6] max-w-[720px]"
            style={{ color: "var(--background-text, #64748B)", fontFamily: "var(--body-font-family, Inter)" }}
          >
            {slideData?.subtitle}
          </p>

          {/* Timeline */}
          <div className="mt-10 relative">
            {/* Timeline line */}
            <div className="absolute top-10 left-0 right-0 h-[3px] rounded-full" style={{ backgroundColor: "var(--primary-color, #E8192D)", opacity: 0.3 }}></div>

            {/* Events */}
            <div
              className="grid gap-0"
              style={{
                gridTemplateColumns: `repeat(${Math.min(events.length, 5)}, minmax(0, 1fr))`,
              }}
            >
              {events.slice(0, 5).map((e, i) => (
                <div key={i} className="relative flex flex-col items-center px-3">
                  {/* Dot on timeline */}
                  <div
                    className="w-4 h-4 rounded-full relative z-10 mb-4 border-[3px]"
                    style={{
                      backgroundColor: "var(--background-color, #FFFFFF)",
                      borderColor: "var(--primary-color, #E8192D)",
                    }}
                  ></div>

                  {/* Year */}
                  <div
                    className="text-[13px] font-bold tracking-wide mb-2"
                    style={{ color: "var(--primary-color, #E8192D)", fontFamily: "var(--body-font-family, Inter)" }}
                  >
                    {e.year}
                  </div>

                  {/* Title */}
                  <div
                    className="text-[16px] font-semibold text-center"
                    style={{ color: "var(--background-text, #00205B)" }}
                  >
                    {e.title}
                  </div>

                  {/* Description */}
                  <p
                    className="mt-2 text-[12px] leading-[1.6] text-center"
                    style={{ color: "var(--background-text, #64748B)", fontFamily: "var(--body-font-family, Inter)" }}
                  >
                    {e.description}
                  </p>
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
export default THYTimelineLayout
