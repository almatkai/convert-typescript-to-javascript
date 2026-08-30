/// <reference types="@raycast/api">

/* 🚧 🚧 🚧
 * This file is auto-generated from the extension's manifest.
 * Do not modify manually. Instead, update the `package.json` file.
 * 🚧 🚧 🚧 */

/* eslint-disable @typescript-eslint/ban-types */

type ExtensionPreferences = {}

/** Preferences accessible in all the extension's commands */
declare type Preferences = ExtensionPreferences

declare namespace Preferences {
  /** Preferences accessible in the `paste-from-clipboard` command */
  export type PasteFromClipboard = ExtensionPreferences & {}
  /** Preferences accessible in the `copy-to-clipboard` command */
  export type CopyToClipboard = ExtensionPreferences & {}
}

declare namespace Arguments {
  /** Arguments passed to the `paste-from-clipboard` command */
  export type PasteFromClipboard = {}
  /** Arguments passed to the `copy-to-clipboard` command */
  export type CopyToClipboard = {}
}

