import { describe, it, expect, vi } from "vitest";
import bus from "./bus";

describe("toast bus", () => {
  it("emits and receives events", () => {
    const handler = vi.fn();
    bus.on("show", handler);
    bus.emit("show", { message: "hi" });
    expect(handler).toHaveBeenCalledWith({ message: "hi" });
  });

  it("stops receiving after off", () => {
    const handler = vi.fn();
    bus.on("clear", handler);
    bus.off("clear", handler);
    bus.emit("clear");
    expect(handler).not.toHaveBeenCalled();
  });
});
