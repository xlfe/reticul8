(ns reticul8.protobuf
    (:require
      [clojure.core.async :as async]
      [protobuf.core :as protobuf]
      [PJON.core :as PJON])

    (:import (net.xlfe.reticul8 Reticul8$FROM_MICRO Reticul8$RPC Reticul8$PING)))


(defn from-micro
 [data]
 (protobuf/create Reticul8$FROM_MICRO (new java.io.ByteArrayInputStream data)))

(defn ping
  [_]
  (protobuf/create Reticul8$RPC {:msg_id _ :ping (protobuf/create Reticul8$PING {:ping true})}))

