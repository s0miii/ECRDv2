"use client";

import { AppProgressBar as ProgressBar } from "next-nprogress-bar";

export default function TopLoader() {
  return (
    <ProgressBar
      height="20px"
      color="#fcb315"
      options={{ showSpinner: false }}
      shallowRouting
    />
  );
}
