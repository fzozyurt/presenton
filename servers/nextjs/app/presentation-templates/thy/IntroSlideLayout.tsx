import React from "react"
import * as z from "zod"

const layoutId = "THYIntroSlideLayout"
const layoutName = "THY Intro Slide"
const layoutDescription = "Turkish Airlines branded cover slide with title, subtitle and accent stripes"

const ImageSchema = z
  .object({
    __image_url__: z.string().url().default("https://images.unsplash.com/photo-1436491865332-7a61a109bb05?w=1200&q=80&auto=format&fit=crop"),
    __image_prompt__: z.string().min(0).max(120).default("airplane wing above clouds"),
  })
  .default({
    __image_url__:
      "https://images.unsplash.com/photo-1436491865332-7a61a109bb05?w=1200&q=80&auto=format&fit=crop",
    __image_prompt__: "airplane wing above clouds",
  })

const Schema = z
  .object({
    title: z
      .string()
      .min(8)
      .max(72)
      .default("Turkish Airlines")
      .meta({ description: "Main slide title" }),

    subtitle: z
      .string()
      .min(8)
      .max(90)
      .default("Elevating Your Journey")
      .meta({ description: "Subtitle below main title" }),

    tagline: z
      .string()
      .min(10)
      .max(140)
      .default("Widen Your World with award-winning service and global connectivity")
      .meta({ description: "Descriptive tagline" }),

    presenter: z
      .object({
        name: z.string().min(3).max(40).default("Presenter Name"),
        title: z.string().min(3).max(60).default("Department"),
      })
      .default({ name: "Presenter Name", title: "Department" }),

    media: z
      .object({
        type: z.literal("image").default("image"),
        image: ImageSchema,
      })
      .default({ type: "image", image: ImageSchema.parse({}) }),
  })
  .default({
    title: "Turkish Airlines",
    subtitle: "Elevating Your Journey",
    tagline: "Widen Your World with award-winning service and global connectivity",
    presenter: { name: "Presenter Name", title: "Department" },
    media: { type: "image", image: ImageSchema.parse({}) },
  })

type SlideData = z.infer<typeof Schema>

interface SlideLayoutProps {
  data?: Partial<SlideData>
}

const THYIntroSlideLayout: React.FC<SlideLayoutProps> = ({ data: slideData }) => {
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
        {/* Top accent stripe - THY Red */}
        <div className="absolute top-0 left-0 right-0 h-[6px]" style={{ backgroundColor: "var(--primary-color, #E8192D)" }}></div>

        {/* Header with logo area */}
        <div className="px-14 pt-10 pb-2">
          <div className="flex items-center gap-3">
            {(slideData as any)?._logo_url__ && (
              <img src={(slideData as any)?._logo_url__} alt="logo" className="h-10" />
            )}
            {(slideData as any)?.__companyName__ && (
              <span
                className="text-[14px] tracking-[0.2em] uppercase font-semibold"
                style={{ color: "var(--background-text, #00205B)" }}
              >
                {(slideData as any)?.__companyName__}
              </span>
            )}
          </div>
        </div>

        {/* Main content area */}
        <div className="grid grid-cols-[56%_44%] gap-8 px-14 pt-12 items-center">
          {/* Left: text content */}
          <div>
            <div
              className="inline-block mb-6 px-4 py-1.5 rounded-full text-[11px] tracking-[0.15em] uppercase font-semibold"
              style={{
                backgroundColor: "var(--primary-color, #E8192D)",
                color: "var(--primary-text, #FFFFFF)",
              }}
            >
              Corporate Presentation
            </div>

            <h1
              className="text-[60px] leading-[1.08] tracking-tight font-bold"
              style={{ color: "var(--background-text, #00205B)" }}
            >
              {slideData?.title}
            </h1>

            <p
              className="mt-4 text-[28px] leading-[1.3] font-light"
              style={{ color: "var(--primary-color, #E8192D)" }}
            >
              {slideData?.subtitle}
            </p>

            <p
              className="mt-6 text-[16px] leading-[1.7] max-w-[520px]"
              style={{ color: "var(--background-text, #64748B)", fontFamily: "var(--body-font-family, Inter)" }}
            >
              {slideData?.tagline}
            </p>

            {/* Presenter info */}
            <div className="mt-10 flex items-center gap-4">
              <div
                className="w-[3px] h-10 rounded-full"
                style={{ backgroundColor: "var(--primary-color, #E8192D)" }}
              ></div>
              <div>
                <div
                  className="text-[15px] font-semibold"
                  style={{ color: "var(--background-text, #00205B)" }}
                >
                  {slideData?.presenter?.name}
                </div>
                <div
                  className="text-[13px]"
                  style={{ color: "var(--background-text, #94A3B8)", fontFamily: "var(--body-font-family, Inter)" }}
                >
                  {slideData?.presenter?.title}
                </div>
              </div>
            </div>
          </div>

          {/* Right: image panel */}
          <div className="relative">
            <div className="overflow-hidden rounded-2xl shadow-2xl aspect-[4/5]">
              <img
                src={slideData?.media?.image?.__image_url__}
                alt={slideData?.media?.image?.__image_prompt__}
                className="w-full h-full object-cover"
              />
            </div>
            {/* Red corner accent */}
            <div
              className="absolute -bottom-3 -right-3 w-20 h-20 rounded-2xl -z-10"
              style={{ backgroundColor: "var(--primary-color, #E8192D)", opacity: 0.15 }}
            ></div>
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
export default THYIntroSlideLayout
