import { mount } from "svelte";
import App from "./App.svelte";

const targetElement = document.getElementById("app");
if (!targetElement) {
  throw new Error("App target element not found");
}
const app = mount(App, {
  target: targetElement,
});

export default app;
