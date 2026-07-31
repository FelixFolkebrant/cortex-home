import { Type } from "typebox";

export const developmentTool = Object.freeze({
  definition: Object.freeze({
    description:
      "Returns a simulated local-development result and never contacts a room or device.",
    label: "Development tool test",
    name: "development_tool_test",
    parameters: Type.Object({}, { additionalProperties: false }),
  }),
  async execute(arguments_) {
    if (
      arguments_ === null ||
      typeof arguments_ !== "object" ||
      Array.isArray(arguments_) ||
      Object.keys(arguments_).length !== 0
    ) {
      throw new Error("invalid_development_tool_arguments");
    }
    return "Simulated development result: no room hardware was contacted or observed.";
  },
});
