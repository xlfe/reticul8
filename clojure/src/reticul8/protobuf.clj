(ns reticul8.protobuf
    (:require
      [clojure.core.async :as async]
      [protobuf.core :as protobuf]
      [PJON.core :as PJON])

    (:import (net.xlfe.reticul8 Reticul8$FROM_MICRO)))


(defn from-micro
 [data]
 (protobuf/create Reticul8$FROM_MICRO (new java.io.ByteArrayInputStream data)))


