(ns reticul8.core
    (:gen-class)
    (:require
      [clojure.core.async :as async]
      [reticul8.protobuf :as pb]
      [protobuf.core :as protobuf]
      [PJON.core :as PJON]))


(def serial-port "/dev/tty.wchusbserial1410")

(defn -main
      []
      (let [incoming (async/chan)
            outgoing (async/chan)]
           (async/<!! (async/go
                        (PJON/transport-loop serial-port incoming outgoing)
                        (loop
                          [packet (async/<!! incoming)
                           i 0]
                          (if (contains? packet :data)
                              (do
                                  (println
                                    (dissoc
                                      (assoc packet
                                             :message (dissoc (pb/from-micro (byte-array (:data packet))) :raw))
                                      :data))
                                  (async/put!
                                    outgoing
                                    {
                                     :receiver-id 11
                                     :sender-id 10
                                     :header #{:ack}
                                     :data (byte-array
                                                       (protobuf/->bytes (pb/ping i)))})
                                  (recur (async/<!! incoming) (inc i)))
                              (println (str "ERROR: " (:error packet)))))))))
