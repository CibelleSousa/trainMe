import { createRoot } from "react-dom/client";
import "../src/gym.css";
import { Index } from "../src/routes/index";

createRoot(document.getElementById("root")!).render(<Index />);
