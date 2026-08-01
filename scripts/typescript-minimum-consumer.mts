import { Result, TaggedError, matchErrorPartial } from "better-result";

class MinimumVersionError extends TaggedError("MinimumVersionError")<{
  message: string;
}> {}

const result = Result.err(new MinimumVersionError({ message: "minimum version smoke test" }));
const message = matchErrorPartial(result.error, {
  MinimumVersionError: (error) => error.message,
});

void message;
