import React from "react"
import * as z from "zod"

const layoutId = "THYClosingSlideLayout"
const layoutName = "THY Closing Slide"
const layoutDescription = "Turkish Airlines branded closing slide with thank you message and contact information"

const ImageSchema = z
  .object({
    __image_url__: z.string().url().default("https://images.unsplash.com/photo-1506012787146-f92b2d7d6d96?w=1200&q=80&auto=format&fit=crop"),
    __image_prompt__: z.string().min(0).max(120).default("airplane flying at sunset over clouds"),
  })
  .default({
    __image_url__:
      "https://images.unsplash.com/photo-1506012787146-f92b2d7d6d96?w=1200&q=80&auto=format&fit=crop",
    __image_prompt__: "airplane flying at sunset over clouds",
  })

const Schema = z
  .object({
    title: z
      .string()
      .min(4)
      .max(48)
      .default("Tesekkurler")
      .meta({ description: "Main thank you title" }),

    subtitle: z
      .string()
      .min(4)
      .max(48)
      .default("Thank You")
      .meta({ description: "Subtitle in English or secondary language" }),

    message: z
      .string()
      .min(10)
      .max(160)
      .default("We look forward to building a brighter future together. Safe travels.")
      .meta({ description: "Closing message" }),

    contacts: z
      .array(
        z.object({
          label: z.string().min(2).max(20).default("Email"),
          value: z.string().min(4).max(60).default("contact@thy.com"),
        })
      )
      .min(1)
      .max(3)
      .default([
        { label: "Email", value: "corporate@thy.com" },
        { label: "Phone", value: "+90 212 444 0 849" },
        { label: "Web", value: "turkishairlines.com" },
      ]),

    media: z
      .object({
        type: z.literal("image").default("image"),
        image: ImageSchema,
      })
      .default({ type: "image", image: ImageSchema.parse({}) }),
  })
  .default({
    title: "Tesekkurler",
    subtitle: "Thank You",
    message: "We look forward to building a brighter future together. Safe travels.",
    contacts: [
      { label: "Email", value: "corporate@thy.com" },
      { label: "Phone", value: "+90 212 444 0 849" },
      { label: "Web", value: "turkishairlines.com" },
    ],
    media: { type: "image", image: ImageSchema.parse({}) },
  })

type SlideData = z.infer<typeof Schema>

interface SlideLayoutProps {
  data?: Partial<SlideData>
}

const THYClosingSlideLayout: React.FC<SlideLayoutProps> = ({ data: slideData }) => {
  const contacts = slideData?.contacts || []
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
          backgroundColor: "var(--background-text, #00205B)",
        }}
      >
        {/* Background image overlay */}
        <div className="absolute inset-0">
          <img
            src={slideData?.media?.image?.__image_url__}
            alt={slideData?.media?.image?.__image_prompt__}
            className="w-full h-full object-cover"
          />
          <div
            className="absolute inset-0"
            style={{
              background: "linear-gradient(135deg, rgba(0,32,91,0.92) 0%, rgba(0,32,91,0.78) 40%, rgba(232,25,45,0.35) 100%)",
            }}
          ></div>
        </div>

        {/* Content */}
        <div className="relative z-10 h-full flex flex-col justify-center px-20">
          <div>
            <div
              className="inline-block mb-6 px-5 py-2 rounded-full text-[12px] tracking-[0.2em] uppercase font-semibold"
              style={{
                backgroundColor: "var(--primary-color, #E8192D)",
                color: "var(--primary-text, #FFFFFF)",
              }}
            >
              {slideData?.subtitle}
            </div>

            <h1
              className="text-[80px] leading-[1.05] font-bold"
              style={{ color: "#FFFFFF" }}
            >
              {slideData?.title}
            </h1>

            <p
              className="mt-6 text-[18px] leading-[1.7] max-w-[600px]"
              style={{ color: "rgba(255,255,255,0.85)", fontFamily: "var(--body-font-family, Inter)" }}
            >
              {slideData?.message}
            </p>

            {/* Contact info */}
            <div className="mt-10 flex gap-10">
              {contacts.slice(0, 3).map((c, i) => (
                <div key={i} className="flex items-center gap-3">
                  <div
                    className="w-[2px] h-10 rounded-full"
                    style={{ backgroundColor: "var(--primary-color, #E8192D)" }}
                  ></div>
                  <div>
                    <div
                      className="text-[11px] tracking-[0.15em] uppercase font-medium"
                      style={{ color: "rgba(255,255,255,0.5)", fontFamily: "var(--body-font-family, Inter)" }}
                    >
                      {c.label}
                    </div>
                    <div
                      className="text-[15px] font-semibold"
                      style={{ color: "#FFFFFF" }}
                    >
                      {c.value}
                    </div>
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
            style={{ color: "rgba(255,255,255,0.6)" }}
          >
            Turkish Airlines
          </span>
          <div className="h-[1px] flex-1" style={{ backgroundColor: "rgba(255,255,255,0.15)" }}></div>
          <span
            className="text-[12px] tracking-wide"
            style={{ color: "rgba(255,255,255,0.4)" }}
          >
            turkishairlines.com
          </span>
        </div>
      </div>
    </>
  )
}

export { Schema, layoutId, layoutName, layoutDescription }
export default THYClosingSlideLayout
