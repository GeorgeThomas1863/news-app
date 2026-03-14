//FOR TESTING ONLY WILL DELETE
export const SAMPLE_DATA = {
  topNews: [
    {
      headline: "AI chip exports face sweeping new restrictions as geopolitical tensions reshape global supply chains",
      source: "Reuters",
      time: "1h ago",
    },
    {
      headline: "Senate passes infrastructure bill after months of gridlock in rare bipartisan vote",
      source: "AP News",
      time: "3h ago",
    },
    {
      headline: "Markets rally as inflation data comes in below expectations for third straight month",
      source: "Bloomberg",
      time: "2h ago",
    },
    {
      headline: "WHO ends mpox public health emergency as global case counts drop significantly",
      source: "BBC",
      time: "5h ago",
    },
  ],

  categories: [
    {
      id: "technology",
      name: "Technology",
      color: "#185FA5",
      expanded: true,
      stories: [
        { headline: "Apple chip promises 40% efficiency gains over current silicon generation", source: "The Verge", time: "2h ago" },
        { headline: "Open-source model beats GPT-4 on standard benchmarks with fraction of parameters", source: "MIT Tech Review", time: "5h ago" },
        { headline: "Quantum startup claims first fault-tolerant processor at room temperature", source: "Wired", time: "6h ago" },
      ],
    },
    {
      id: "politics",
      name: "Politics",
      color: "#A32D2D",
      expanded: true,
      stories: [
        { headline: "EU summit ends without agreement on joint energy policy framework", source: "BBC", time: "4h ago" },
        { headline: "Federal court blocks new immigration directive pending further review", source: "Reuters", time: "7h ago" },
        { headline: "Treasury secretary signals openness to debt ceiling negotiations", source: "AP News", time: "9h ago" },
      ],
    },
    {
      id: "business",
      name: "Business",
      color: "#3B6D11",
      expanded: false,
      stories: [
        { headline: "Fed signals pause in rate hikes as economic data continues to soften", source: "Bloomberg", time: "1h ago" },
        { headline: "Amazon announces major logistics restructuring across North America", source: "WSJ", time: "3h ago" },
        { headline: "Venture funding rebounds in Q1 after two consecutive years of decline", source: "TechCrunch", time: "8h ago" },
      ],
    },
    {
      id: "world",
      name: "World",
      color: "#854F0B",
      expanded: false,
      stories: [
        { headline: "Ceasefire negotiations resume as regional mediators return to the table", source: "Al Jazeera", time: "2h ago" },
        { headline: "G7 leaders agree on new framework for international AI governance", source: "Reuters", time: "4h ago" },
        { headline: "UN warns of deepening humanitarian crisis across parts of East Africa", source: "BBC", time: "9h ago" },
      ],
    },
    {
      id: "science",
      name: "Science",
      color: "#534AB7",
      expanded: false,
      stories: [
        { headline: "Researchers discover carbon capture method using engineered bacteria", source: "Nature", time: "6h ago" },
        { headline: "NASA confirms presence of water ice deposits near Mars south pole", source: "Space.com", time: "10h ago" },
        { headline: "Study finds deep-ocean microbes producing oxygen without sunlight", source: "Science Daily", time: "12h ago" },
      ],
    },
    {
      id: "health",
      name: "Health",
      color: "#0F6E56",
      expanded: false,
      stories: [
        { headline: "New study links ultra-processed foods to accelerated cognitive decline", source: "NEJM", time: "3h ago" },
        { headline: "FDA approves first over-the-counter hearing aid for mild hearing loss", source: "AP News", time: "6h ago" },
        { headline: "Researchers identify key protein behind treatment-resistant depression", source: "Science Daily", time: "11h ago" },
      ],
    },
  ],
};
