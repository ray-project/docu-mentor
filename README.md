# Doc Sanity

![doc_sanity](https://github.com/ray-project/doc-sanity/assets/3462566/645dd42f-b424-4655-b25e-511527bee9f3)

Automatically get suggestions to improve your PRs from this
GitHub app powered by [Anyscale Endpoints](https://app.endpoints.anyscale.com/).

## Installation

Simply install the app on your project on GitHub: [Doc Sanity App](https://github.com/apps/doc-sanity)

## Usage

Then in any PR in your project, create a new comment that says:

```bash
@doc-sanity run
```

and I will start my analysis. I only look at what you changed
in this PR. If you only want me to look at specific files or folders,
you can specify them like this:

```bash
@doc-sanity run doc/ README.md
```

In this example, I'll have a look at all files contained in the
"doc/" folder and the file "README.md".
