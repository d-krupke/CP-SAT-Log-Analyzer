// Type shim: the minified "basic" Plotly bundle has the same API as plotly.js.
declare module 'plotly.js-basic-dist-min' {
  import * as Plotly from 'plotly.js'
  export = Plotly
}
