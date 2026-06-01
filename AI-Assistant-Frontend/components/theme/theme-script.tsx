const STORAGE_KEY = "theme";

const script = `(function(){try{var s=localStorage.getItem("${STORAGE_KEY}");var t=s==="light"||s==="dark"?s:(window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light");var r=document.documentElement;if(t==="dark"){r.classList.add("dark");}else{r.classList.remove("dark");}r.style.colorScheme=t;}catch(e){}})();`;

export function ThemeScript() {
  return <script dangerouslySetInnerHTML={{ __html: script }} />;
}
