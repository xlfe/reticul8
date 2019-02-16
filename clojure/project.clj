(defproject reticul8 "0.1.0-SNAPSHOT"
  :description "FIXME: write description"
  :url "http://example.com/FIXME"
  :license {:name "Eclipse Public License"
            :url "http://www.eclipse.org/legal/epl-v10.html"}
  :dependencies [
                 [org.clojure/clojure "1.10.0"]
                 [org.clojure/core.async "0.4.474"]
                 ;[clojusc/protobuf "3.5.1-v1.1"]
                 [clojusc/protobuf "3.6.0-v1.2-SNAPSHOT"]
                 [org.clojure/tools.cli "0.4.1"]
                 [net.xlfe/PJON-clojure "0.1.0-SNAPSHOT"]]
  :main ^:skip-aot reticul8.core
  :java-source-paths [
                      "../java/src/net/xlfe/reticul8"
                      "../java/src/fi/kapsi/koti/jpa/nanopb"]
  :target-path "target/%s"
  :profiles {:uberjar {:aot :all}})
